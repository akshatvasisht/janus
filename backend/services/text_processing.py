"""Text processing helpers for receiver-side buffering.

Qwen3-TTS currently does not provide true incremental streaming. To reduce
perceived latency, we buffer text and synthesize at sentence boundaries.

Critical behavior: Janus packets are VAD-delimited turns and may contain no
punctuation. To avoid "hanging text", call `SentenceBuffer.flush()` after feeding
each packet so end-of-packet acts like an implicit full stop.
"""

from __future__ import annotations

from typing import Optional


class SentenceBuffer:
    """
    Buffer tokens until sentence-ending punctuation is observed.

    This is intentionally simple:
    - `add_token()` appends the token and emits a sentence when token is one of:
      '.', '?', '!', '\\n'
    - `flush()` emits any remaining buffered text (used for end-of-packet).
    """

    _END_TOKENS = {".", "?", "!", "\n"}

    def __init__(self) -> None:
        self._buf: str = ""

    def add_token(self, token: str) -> Optional[str]:
        """
        Append a token and optionally emit a completed sentence.

        Args:
            token: Next token (character or word) to append.

        Returns:
            The completed sentence string if token ended the sentence (e.g. '.', '?', '!');
            None otherwise.
        """
        if not token:
            return None

        # Append raw token (works for both char-level and word-level tokenization)
        self._buf += token

        if token in self._END_TOKENS:
            return self.flush()

        return None

    def flush(self) -> Optional[str]:
        """
        Emit any buffered text and clear the buffer.

        Returns:
            The buffered text as a string, or None if the buffer was empty.
        """
        sentence = self._buf.strip()
        self._buf = ""
        return sentence or None


def iter_text_tokens(text: str) -> list[str]:
    """
    Tokenize a full utterance into a sequence of tokens suitable for SentenceBuffer.

    For the current Janus pipeline, char-level tokens are sufficient and preserve
    punctuation reliably.

    Args:
        text: Full utterance string to tokenize.

    Returns:
        List of single-character tokens (or empty list if text is empty/None).
    """
    return list(text or "")

