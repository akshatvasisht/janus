

<img width="1024" height="510" alt="Janus logo final - Copy" src="https://github.com/user-attachments/assets/e9e57755-7e98-4b4b-b75f-d8040d064280" />

# Janus - Real-Time Semantic Audio Codec

Submission for MadHacks 2025

## Overview

Janus is a real-time semantic audio codec system designed to optimize bandwidth by transmitting semantic meaning rather than raw audio waveforms. Instead of sending compressed audio data, Janus converts speech to text, extracts prosodic metadata (pitch and energy), and reconstructs the voice on the receiver side using generative text-to-speech synthesis.

This approach enables high-quality voice communication over extremely constrained network connections (as low as 300bps), then reconstructed into natural-sounding speech using modern generative TTS models.

### Research Inspiration

Janus is inspired by SemantiCodec (Zhang et al., 2024), a state-of-the-art semantic codec that demonstrated the viability of sub-kbps speech transmission by encoding meaning and prosody instead of waveforms. Janus extends this paradigm into a real-time system by leveraging Faster-Whisper for speech-to-text, Silero VAD for precise speech gating, Aubio for pitch/energy extraction, MessagePack for ultra-compact serialization, and FishAudio’s generative TTS in an end-to-end STT → semantic-packet → TTS codec pipeline.

### How Janus Works
1. STT Layer (Faster-Whisper)
   Extracts text and timestamps from live speech.
2. Prosody Layer (Aubio)
   Capture pitch and energy to preserve tone
3. Compression Layer (MessagePack)
   Packages text + prosody into ~300 bps payloads
4. Voice Reconstruction Layer (Fishaudio TTS)
   Generates natural speech using the sender’s message and extracted prosody.

<img width="1897" height="216" alt="image" src="https://github.com/user-attachments/assets/db7cb35e-ae87-4fb7-b0a0-35903f7572a8" />

---

## Impact

Janus achieves significant efficiency gains through semantic compression:

### Performance

- **Operating Bitrate**: 300 bits per second (bps)
- **Comparison to VoIP**: ~20x more efficient than standard VoIP codecs like Opus (which requires minimum ~6 kbps for robust operation)
- **Comparison to SOTA Codecs**: 5-10x more efficient than state-of-the-art neural waveform codecs (Lyra/EnCodec, which reach a physical compression floor at ~1.5-3 kbps)

### Cost Savings

**Pricing Comparison:** Janus achieves a 158x cost reduction for critical satellite communication
- **Standard Satellite Voice** (Iridium Land): ~$0.89 per minute
- **Janus Semantic Voice** (Iridium Certus Data): ~$0.0056 per event

**Operational Impact:** For industrial users operating remote fleets, this nearly eliminates vocal communication expenses
- **Standard Voice OPEX**: $13,350/month for a single fleet
- **Semantic Voice OPEX**: $84/month for the same fleet

### Applications

**Public Safety and Disaster Relief**
- Reliable communication when infrastructure fails during mass casualty events (Maui wildfires, Hurricane Helene)
- Crystal-clear synthesized audio reduces cognitive load on first responders

**Global South and Rural Connectivity**
- Voice over ultra-low-power networks (LoRaWAN, LPWAN) where high-bandwidth is unviable
- Addresses digital divide in underserved regions

**Maritime Communications**
- Primary/backup voice over expensive L-band satellites (Iridium/Inmarsat)
- Eliminates economic friction discouraging detailed voice exchanges at sea

**Smart Mining Operations**
- Coordinates supervisors in remote surface operations
- Maintains communication in subterranean GPS-denied environments

**Low-Power/Off-Grid IoT**
- Voice commands on battery-powered devices and sensor networks
- Complies with strict regulatory duty cycle limits (1% Europe) impossible for continuous voice

## Documentation

- **[SETUP.md](SETUP.md)**: Environment setup, installation, and start instructions
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Architecture, tech stack, and design decisions
- **[API.md](docs/API.md)**: WebSocket and REST API reference
- **[TESTING.md](docs/TESTING.md)**: Testing guidelines
- **[STYLE.md](docs/STYLE.md)**: Coding standards

## License

See **[LICENSE](LICENSE)** file for details.
