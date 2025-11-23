from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from contextlib import asynccontextmanager

# API Routers
# Note: Using relative imports assuming this file is run as a module (e.g. uvicorn backend.server:app)
from .api.endpoints import router as api_router
from .api.socket_manager import router as ws_router

# Engine & State
from .common import engine_state
from .services.engine import smart_ear_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Smart Ear Engine...")

    # Ensure queues are initialized on the running loop
    transcript_queue = engine_state.get_transcript_queue()
    packet_queue = engine_state.get_packet_queue()

    # Launch the Smart Ear engine as a background task
    task = asyncio.create_task(
        smart_ear_loop(
            control_state=engine_state.control_state,
            transcript_queue=transcript_queue,
            packet_queue=packet_queue,
        )
    )

    yield

    # Shutdown logic
    # We could gracefully cancel the task here if we stored reference to it
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Smart Ear Engine stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Janus Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS (Allow frontend access)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(api_router, prefix="/api")
    app.include_router(ws_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    # If run directly, assume we are in the backend directory
    uvicorn.run(app, host="0.0.0.0", port=8000)
