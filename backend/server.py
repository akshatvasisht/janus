import asyncio
import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.endpoints import router as api_router
from .api.socket_manager import router as ws_router
from .common import engine_state
from .services.audio_io import AudioService
from .services.engine import receiver_loop, smart_ear_loop

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "janus.log")

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        file_handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Manages startup and shutdown of the Smart Ear engine, including audio service
    initialization, background tasks, and receiver loop thread.
    
    Args:
        app: FastAPI application instance.
    
    Yields:
        None: Control is yielded to the application runtime.
    """
    logger.info("Starting Smart Ear Engine...")

    # Initialize shared AudioService for full-duplex audio
    global_audio_service = AudioService()
    
    # Create stop event for receiver loop
    receiver_stop_event = threading.Event()

    # Ensure queues are initialized on the running loop
    transcript_queue = engine_state.get_transcript_queue()
    packet_queue = engine_state.get_packet_queue()
    
    # Get the event loop for async operations in receiver_loop
    event_loop = asyncio.get_running_loop()

    # Launch the Smart Ear engine as a background task
    task = asyncio.create_task(
        smart_ear_loop(
            control_state=engine_state.control_state,
            transcript_queue=transcript_queue,
            packet_queue=packet_queue,
            audio_service=global_audio_service,
        )
    )

    # Start receiver loop in a separate thread
    receiver_thread = threading.Thread(
        target=receiver_loop,
        args=(global_audio_service, receiver_stop_event, event_loop),
        daemon=True
    )
    receiver_thread.start()
    logger.info("Receiver loop started.")

    yield

    # Shutdown logic
    logger.info("Shutting down...")
    
    # Signal receiver loop to stop
    receiver_stop_event.set()
    
    # Wait for receiver thread to finish (with timeout)
    receiver_thread.join(timeout=2)
    
    # Cancel the Smart Ear engine task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Close shared audio service
    global_audio_service.close()
    
    logger.info("Smart Ear Engine stopped.")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Sets up CORS middleware and registers API and WebSocket routers.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Janus Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(ws_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    # If run directly, assume we are in the backend directory
    uvicorn.run(app, host="0.0.0.0", port=8000)
