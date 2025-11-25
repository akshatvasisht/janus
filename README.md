# Janus - Real-Time Semantic Audio Codec

Janus is a real-time semantic audio codec system designed to optimize bandwidth by transmitting semantic meaning rather than raw audio waveforms. Instead of sending compressed audio data, Janus converts speech to text, extracts prosodic metadata (pitch and energy), and reconstructs the voice on the receiver side using generative text-to-speech synthesis.

This approach enables high-quality voice communication over extremely constrained network connections (as low as 300bps), then reconstructed into natural-sounding speech using modern generative TTS models.

## Quick Start

1. **Setup**: Follow the instructions in [SETUP.md](SETUP.md) to install dependencies and configure the environment
2. **Run Backend**: Start the FastAPI server with `uvicorn backend.server:app --reload`
3. **Run Frontend**: Start the Next.js development server with `cd frontend && npm run dev`
4. **Access**: Open `http://localhost:3000` in your browser

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Project Structure

```
MadHacks/
├── backend/           # Python FastAPI backend
│   ├── api/          # REST and WebSocket endpoints
│   ├── common/       # Protocol and state management
│   ├── services/     # Audio processing services
│   ├── scripts/      # CLI utility tools
│   ├── tests/        # Test suite
│   └── server.py     # Backend entry point
├── frontend/         # Next.js React application
│   ├── app/          # Next.js pages
│   ├── components/   # React components
│   ├── hooks/        # Custom hooks
│   └── types/        # TypeScript types
├── docs/             # Documentation
└── SETUP.md          # Setup instructions
```

## Documentation

- **[SETUP.md](SETUP.md)**: Environment setup and installation
- **[docs/projectdocs.md](docs/projectdocs.md)**: Architecture, tech stack, and design decisions
- **[docs/API.md](docs/API.md)**: WebSocket and REST API reference
- **[docs/TESTING.md](docs/TESTING.md)**: Testing guidelines
- **[docs/STYLE.md](docs/STYLE.md)**: Coding standards

## License

See **[LICENSE](LICENSE)** file for details.
