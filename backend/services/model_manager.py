"""
Model Manager service for Qwen3-TTS local inference.

This module provides a Singleton-style `ModelManager` that:
- Loads the Qwen3-TTS-12Hz-0.6B-Base model once into memory
- Detects the best available device (CUDA, MPS, or CPU)
- Optionally applies 4-bit quantization on CUDA via bitsandbytes
- Optionally wraps the model with `torch.compile` for faster inference
- Exposes a `generate(text, ref_audio_path) -> bytes` API that:
  - Runs voice-clone style inference using reference audio
  - Resamples model output to the AudioService sample rate (44.1kHz)
  - Returns int16 PCM bytes suitable for PyAudio playback

This implementation validates expected input/output shapes and raises a
descriptive RuntimeError when the underlying backend API is incompatible.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import soundfile as sf
import librosa
from transformers import AutoModel, AutoProcessor

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton manager for the Qwen3-TTS model.

    Usage:
        manager = ModelManager()
        audio_bytes = manager.generate("Hello world")
    """

    _instance: Optional["ModelManager"] = None
    _initialized: bool = False

    def __new__(cls, *args: object, **kwargs: object) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_id: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        ref_audio_path: Optional[str] = None,
        output_sample_rate: int = 44_100,
        enable_compile: bool = True,
    ) -> None:
        """
        Initialize the ModelManager singleton.

        Args:
            model_id: Hugging Face model ID for Qwen3-TTS.
            ref_audio_path: Path to enrollment/reference audio. Defaults to
                backend/assets/enrollment.wav.
            output_sample_rate: Target sample rate for playback (must match
                AudioService / PyAudio).
            enable_compile: Whether to attempt torch.compile for speedup.
        """
        if self._initialized:
            return

        self.model_id = model_id
        self.output_sample_rate = output_sample_rate

        # Hugging Face hub uses symlinks by default for cache snapshots. In some
        # environments (notably certain container/sandbox/WSL setups), symlinks
        # can fail and leave snapshot directories empty. Disable symlinks by
        # default to make model downloads reliable.
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

        # Default reference audio path (created if missing)
        self.ref_audio_path = ref_audio_path or self._default_ref_audio_path()
        self._ensure_reference_audio_exists(self.ref_audio_path)

        # Fast path for unit tests / environments where loading is undesirable.
        # NOTE: generate() will raise until the model is loaded.
        if os.getenv("JANUS_QWEN3_TTS_DRY_RUN"):
            self.device = "cpu"
            self.torch_dtype = torch.float32
            self.quantization_config = None
            self.processor = None
            self.model = None
            self.model_sample_rate = self.output_sample_rate
            self._initialized = True
            logger.warning(
                "ModelManager initialized in dry-run mode "
                "(JANUS_QWEN3_TTS_DRY_RUN=1): model weights not loaded."
            )
            return

        # Device + dtype + optional quantization config
        (
            self.device,
            self.torch_dtype,
            self.quantization_config,
        ) = self._select_device_and_dtype()

        logger.info(
            "Loading Qwen3-TTS model %s on %s (dtype=%s, quantized=%s)",
            self.model_id,
            self.device,
            self.torch_dtype,
            bool(self.quantization_config),
        )

        # Prefer the official Qwen3-TTS wrapper (qwen-tts). It still uses the
        # Hugging Face Hub for weights, but avoids AutoConfig mapping issues.
        self.backend = "transformers"
        self.processor = None
        self.model = None

        try:
            from qwen_tts import Qwen3TTSModel  # type: ignore

            self.backend = "qwen_tts"
            # qwen-tts forwards kwargs to Transformers' AutoModel.from_pretrained(...),
            # so we can pass both `attn_implementation` and (optionally) a
            # `quantization_config` on CUDA.
            base_kwargs = {
                "device_map": "auto",
                # NOTE: qwen-tts docs/examples use `dtype=...`.
                "dtype": self.torch_dtype,
            }
            # Phase 2 spec: set attention implementation at load time.
            preferred_kwargs = {
                **base_kwargs,
                "attn_implementation": "sdpa",
            }
            if self.quantization_config is not None:
                preferred_kwargs["quantization_config"] = self.quantization_config

            try:
                self.model = Qwen3TTSModel.from_pretrained(self.model_id, **preferred_kwargs)
            except Exception as exc:
                # Fallback order:
                # 1) Drop attn_implementation (some builds may not support it)
                # 2) Drop quantization_config (if 4-bit load is unsupported)
                logger.warning(
                    "qwen-tts preferred load kwargs failed (%s). Retrying with reduced settings.",
                    exc,
                )
                retry_kwargs = dict(base_kwargs)
                if self.quantization_config is not None:
                    retry_kwargs["quantization_config"] = self.quantization_config
                try:
                    self.model = Qwen3TTSModel.from_pretrained(self.model_id, **retry_kwargs)
                except Exception as exc2:
                    logger.warning(
                        "qwen-tts quantized load failed (%s). Retrying without quantization.",
                        exc2,
                    )
                    self.model = Qwen3TTSModel.from_pretrained(self.model_id, **base_kwargs)

            logger.info("Loaded Qwen3-TTS via qwen-tts backend.")
        except Exception as exc:
            logger.warning(
                "qwen-tts backend unavailable or failed to load (%s). Falling back to transformers AutoModel.",
                exc,
            )

        if self.model is None:
            # Load processor (handles text + audio inputs)
            # MCP (Hugging Face) usage point:
            # - Verify that AutoProcessor with trust_remote_code handles Qwen3-TTS
            self.processor = AutoProcessor.from_pretrained(
                self.model_id,
                trust_remote_code=True,
            )

            # Load model with optional quantization
            model_kwargs = {
                "torch_dtype": self.torch_dtype,
                "device_map": "auto",
                "trust_remote_code": True,
            }
            if self.quantization_config is not None:
                model_kwargs["quantization_config"] = self.quantization_config

            # MCP (Hugging Face) usage point:
            # - Confirm that AutoModel with trust_remote_code returns Qwen3TTSModel
            self.model = AutoModel.from_pretrained(self.model_id, **model_kwargs)

        # Try to enable SDPA/Flash Attention when supported
        self._configure_attention()

        # Optional torch.compile for speedup
        if enable_compile and hasattr(torch, "compile"):
            if self.backend == "qwen_tts":
                # qwen-tts is a wrapper object, but it exposes the underlying
                # torch.nn.Module on `self.model.model` (see upstream qwen-tts).
                try:
                    inner = getattr(self.model, "model", None)
                    if inner is not None:
                        self.model.model = torch.compile(inner, mode="reduce-overhead")
                        logger.info("torch.compile enabled for Qwen3-TTS (qwen-tts backend).")
                    else:
                        logger.warning(
                            "torch.compile skipped: qwen-tts wrapper did not expose `.model`."
                        )
                except Exception as exc:
                    logger.warning("torch.compile failed, continuing without it: %s", exc)
            else:
                self._maybe_compile_model()

        # Infer model's native sample rate from processor or config
        self.model_sample_rate = self._infer_model_sample_rate()
        logger.info(
            "Inferred model native sample rate: %s Hz",
            self.model_sample_rate,
        )

        # Cold-start warmup to shift first-run latency to startup
        self._warmup()

        self._initialized = True

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate(self, text: str, ref_audio_path: Optional[str] = None) -> bytes:
        """
        Generate voice-cloned audio for the given text.

        Args:
            text: Text to synthesize.
            ref_audio_path: Optional override for reference audio path.

        Returns:
            bytes: Int16 PCM audio bytes resampled to `output_sample_rate`.
        """
        if not text:
            return b""

        if getattr(self, "model", None) is None:
            raise RuntimeError(
                "ModelManager is not fully initialized (model not loaded). "
                "Unset JANUS_QWEN3_TTS_DRY_RUN to enable real inference."
            )

        path = ref_audio_path or self.ref_audio_path
        if not path:
            raise RuntimeError(
                "ModelManager.generate called without a valid reference audio path."
            )
        self._ensure_reference_audio_exists(path)

        # Core inference: get float32 waveform at model's native sample rate
        audio_f32, native_sr = self._run_inference(text, path)

        # Critical: Sample rate resampling to match AudioService (PyAudio)
        target_sr = self.output_sample_rate
        if native_sr != target_sr:
            logger.debug(
                "Resampling model output from %s Hz to %s Hz",
                native_sr,
                target_sr,
            )
            audio_f32 = librosa.resample(
                audio_f32, orig_sr=native_sr, target_sr=target_sr
            )
            native_sr = target_sr

        # Ensure mono channel
        if audio_f32.ndim > 1:
            audio_f32 = audio_f32.mean(axis=-1)

        # Convert to int16 PCM bytes for PyAudio
        audio_int16 = np.clip(audio_f32, -1.0, 1.0)
        audio_int16 = (audio_int16 * 32767.0).astype(np.int16)
        return audio_int16.tobytes()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _ensure_reference_audio_exists(self, ref_audio_path: str) -> None:
        """
        Ensure a reference audio file exists at the given path.

        Phase 2 requires a default enrollment/reference clip. If the asset is
        missing (common in fresh clones), generate a short 3-second 440Hz sine
        wave placeholder.
        """
        try:
            path = Path(ref_audio_path)
            if path.exists() and path.is_file():
                return

            path.parent.mkdir(parents=True, exist_ok=True)

            duration_s = 3.0
            sr = self.output_sample_rate
            t = np.linspace(0.0, duration_s, int(sr * duration_s), endpoint=False)
            wave = 0.2 * np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)

            sf.write(str(path), wave, sr, subtype="PCM_16")
            logger.warning(
                "Reference audio was missing; generated placeholder enrollment.wav at %s",
                str(path),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to ensure reference audio exists at {ref_audio_path}: {exc}"
            ) from exc

    def _select_device_and_dtype(
        self,
    ) -> Tuple[str, torch.dtype, Optional[object]]:
        """
        Select the best available device and dtype, with optional 4-bit quantization.

        Returns:
            (device_str, torch_dtype, quantization_config_or_None)
        """
        quantization_config = None

        if torch.cuda.is_available():
            device = "cuda"
            dtype = torch.float16

            # CUDA-only 4-bit quantization via bitsandbytes
            try:
                from transformers import BitsAndBytesConfig

                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                )
            except Exception as exc:
                logger.warning(
                    "bitsandbytes 4-bit quantization unavailable: %s", exc
                )
                quantization_config = None

        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            # Mac MPS backend: float16, no 4-bit quantization
            device = "mps"
            dtype = torch.float16
        else:
            # CPU fallback: float32 for maximum compatibility
            device = "cpu"
            dtype = torch.float32

        return device, dtype, quantization_config

    def _configure_attention(self) -> None:
        """
        Try to enable SDPA / Flash Attention 2 where supported.
        """
        try:
            if hasattr(self.model, "config"):
                # Some models expose attn_implementation on config
                if getattr(self.model.config, "attn_implementation", None) is None:
                    self.model.config.attn_implementation = "sdpa"
        except Exception as exc:
            logger.warning("Failed to configure SDPA attention: %s", exc)

    def _maybe_compile_model(self) -> None:
        """
        Attempt to wrap the model with torch.compile for a speedup.
        """
        try:
            self.model = torch.compile(self.model, mode="reduce-overhead")
            logger.info("torch.compile enabled for Qwen3-TTS model.")
        except Exception as exc:
            # Common failure on some MPS / MacOS configurations
            logger.warning("torch.compile failed, continuing without it: %s", exc)

    def _infer_model_sample_rate(self) -> int:
        """
        Infer the model's native sample rate from processor or config.

        Returns:
            int: Sample rate in Hz (falls back to 24kHz if unknown).
        """
        sr: Optional[int] = None

        # Prefer qwen-tts model metadata if available
        if getattr(self, "backend", None) == "qwen_tts":
            for attr in ("sampling_rate", "sample_rate", "audio_sample_rate"):
                value = getattr(self.model, attr, None)
                if isinstance(value, int) and value > 0:
                    sr = value
                    break

        # Prefer processor feature_extractor if available
        if sr is None and getattr(self, "processor", None) is not None:
            feature_extractor = getattr(self.processor, "feature_extractor", None)
            if feature_extractor is not None:
                sr = getattr(feature_extractor, "sampling_rate", None)

        # Fallback to model config attributes
        if sr is None and hasattr(self.model, "config"):
            for attr in ("sample_rate", "audio_sample_rate"):
                value = getattr(self.model.config, attr, None)
                if isinstance(value, int) and value > 0:
                    sr = value
                    break

        # Conservative default if nothing is specified
        if sr is None:
            logger.warning(
                "Could not infer model sample rate from processor/config; "
                "defaulting to 24000 Hz."
            )
            sr = 24_000

        return sr

    def _default_ref_audio_path(self) -> str:
        """
        Resolve the default enrollment/reference audio path.

        Returns:
            str: Absolute path to backend/assets/enrollment.wav
        """
        backend_root = Path(__file__).resolve().parent.parent
        default_path = backend_root / "assets" / "enrollment.wav"
        return str(default_path)

    def _warmup(self) -> None:
        """
        Perform a dummy inference to warm up the model execution graph.
        """
        try:
            if not self.ref_audio_path:
                logger.warning(
                    "Skipping warmup: no reference audio path configured."
                )
                return

            logger.info("Running warmup inference for Qwen3-TTS model...")
            # Minimal, deterministic warmup. We cannot guarantee "silence" from a
            # TTS model on demand, but we can ensure a real forward pass happens.
            self._run_inference(
                "Warmup.",
                self.ref_audio_path,
                generation_kwargs={
                    "do_sample": False,
                    "max_new_tokens": 64,
                },
            )
            logger.info("Warmup inference completed.")
        except Exception as exc:
            # Warmup failures should not crash the server; they only affect latency
            logger.warning("Warmup inference failed: %s", exc)

    def _run_inference(
        self,
        text: str,
        ref_audio_path: str,
        *,
        generation_kwargs: Optional[dict] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Internal helper: run model inference and return raw waveform.

        Args:
            text: Text to synthesize.
            ref_audio_path: Path to reference audio file.

        Returns:
            (audio_float32, sample_rate)
        """
        gen_kwargs = generation_kwargs or {}

        # If using qwen-tts backend, call its voice-clone API directly.
        if getattr(self, "backend", None) == "qwen_tts":
            try:
                wavs, sr = self.model.generate_voice_clone(
                    text=text,
                    ref_audio=ref_audio_path,
                    # For Base models, ref_text is required in ICL mode.
                    # Our default enrollment clip is synthetic and has no transcript,
                    # so use x-vector-only cloning (speaker embedding only).
                    x_vector_only_mode=True,
                    **gen_kwargs,
                )
            except TypeError:
                # Some versions may not support x_vector_only_mode kwarg
                wavs, sr = self.model.generate_voice_clone(
                    text=text,
                    ref_audio=ref_audio_path,
                    **gen_kwargs,
                )

            # wavs is typically a list[np.ndarray]
            if isinstance(wavs, (list, tuple)) and len(wavs) > 0:
                audio_f32 = np.asarray(wavs[0], dtype=np.float32)
            else:
                audio_f32 = np.asarray(wavs, dtype=np.float32)

            # Ensure mono
            if audio_f32.ndim > 1:
                audio_f32 = audio_f32.mean(axis=-1)

            return audio_f32, int(sr)

        # Transformers backend: load reference audio (float32, mono)
        audio, sr = sf.read(ref_audio_path, dtype="float32", always_2d=False)

        # Downmix stereo to mono if needed
        if audio.ndim > 1:
            audio = audio.mean(axis=-1)

        # Resample reference audio to model's expected sample rate
        if sr != self.model_sample_rate:
            logger.debug(
                "Resampling reference audio from %s Hz to %s Hz",
                sr,
                self.model_sample_rate,
            )
            audio = librosa.resample(
                audio, orig_sr=sr, target_sr=self.model_sample_rate
            )
            sr = self.model_sample_rate

        # Prepare inputs via processor
        # MCP (Hugging Face) usage point:
        # - Confirm exact processor signature for Qwen3-TTS (text + audio fields)
        if self.processor is None:
            raise RuntimeError(
                "Transformers backend selected but processor is not initialized."
            )
        inputs = None
        processor_errors: list[str] = []
        for kwargs in (
            {"text": text, "audio": audio, "sampling_rate": sr},
            {"text": text, "audios": audio, "sampling_rate": sr},
            {"text": [text], "audio": [audio], "sampling_rate": sr},
            {"text": [text], "audios": [audio], "sampling_rate": sr},
        ):
            try:
                inputs = self.processor(return_tensors="pt", **kwargs)
                break
            except Exception as exc:
                processor_errors.append(f"{kwargs.keys()}: {exc}")
                inputs = None

        if inputs is None:
            raise RuntimeError(
                "Failed to build inputs via processor for Qwen3-TTS. "
                f"Tried multiple signatures; errors: {processor_errors}"
            )

        # Move tensors to target device
        for key, value in list(inputs.items()):
            if isinstance(value, torch.Tensor):
                inputs[key] = value.to(self.device)

        # Run generation
        with torch.no_grad():
            if hasattr(self.model, "generate_voice_clone"):
                # Some Qwen3-TTS implementations expose a dedicated voice-clone entrypoint.
                # Prefer it if present, but keep a fallback to `generate`.
                try:
                    outputs = self.model.generate_voice_clone(**inputs, **gen_kwargs)
                except TypeError:
                    outputs = self.model.generate(**inputs, **gen_kwargs)
            else:
                outputs = self.model.generate(**inputs, **gen_kwargs)

        audio_f32, native_sr = self._extract_audio_from_output(outputs)
        if native_sr is None:
            native_sr = self.model_sample_rate

        return audio_f32.astype("float32"), native_sr

    def _extract_audio_from_output(
        self,
        outputs,
    ) -> Tuple[np.ndarray, Optional[int]]:
        """
        Extract audio waveform and sample rate from model outputs.

        The exact structure of outputs can vary depending on the implementation.
        This helper attempts several common patterns:
        - Dict with "audio_values" (and optional "sampling_rate")
        - Tuple/list where the first element is a tensor/ndarray
        - Plain tensor

        Returns:
            (audio_float32, sample_rate_or_None)
        """
        # Attribute-style outputs (e.g., ModelOutput with .audio_values / .sampling_rate)
        if not isinstance(outputs, dict) and hasattr(outputs, "__dict__"):
            audio_attr = None
            for name in ("audio_values", "audio", "audios", "waveform", "waveforms"):
                if hasattr(outputs, name):
                    audio_attr = getattr(outputs, name)
                    break
            if audio_attr is not None:
                sr_attr = getattr(outputs, "sampling_rate", None)
                outputs = {"audio_values": audio_attr, "sampling_rate": sr_attr}

        # Dict-style output (e.g., { "audio_values": tensor, "sampling_rate": 24000 })
        if isinstance(outputs, dict):
            audio = outputs.get("audio_values", None)
            sr = outputs.get("sampling_rate", None)
            if audio is None:
                raise RuntimeError(
                    "Qwen3-TTS outputs dict did not contain 'audio_values'. "
                    "Please verify the generation API."
                )
        else:
            # Tuple / list: some multimodal models return (text_ids, audio) or (audio, sr)
            if isinstance(outputs, (list, tuple)) and outputs:
                sr = None
                if len(outputs) >= 2 and isinstance(outputs[1], (torch.Tensor, np.ndarray)):
                    audio = outputs[1]
                else:
                    audio = outputs[0]
                if len(outputs) >= 2 and isinstance(outputs[1], int):
                    sr = outputs[1]
                elif len(outputs) >= 3 and isinstance(outputs[2], int):
                    sr = outputs[2]
            else:
                # Plain tensor
                audio = outputs
                sr = None

        # Convert to numpy
        if isinstance(audio, torch.Tensor):
            audio_np = audio.detach().cpu().numpy()
        elif isinstance(audio, np.ndarray):
            audio_np = audio
        else:
            raise RuntimeError(
                f"Unsupported Qwen3-TTS output type for audio: {type(audio)!r}"
            )

        # Remove batch/channel dimensions if present
        if audio_np.ndim >= 2:
            # Assume shape [batch, time] or [batch, channels, time]
            audio_np = audio_np[0]
        if audio_np.ndim == 2:
            # Downmix channels
            audio_np = audio_np.mean(axis=0)

        return audio_np.astype("float32"), sr


__all__ = ["ModelManager"]

