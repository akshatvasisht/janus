import asyncio
from pydantic import BaseModel
from typing import Optional
from ..api.types import (
    JanusMode,
    EmotionOverride,
    TranscriptMessage,
    PacketSummaryMessage,
)


class ControlState(BaseModel):
    """
    Shared control state, mutated by WebSocket control messages
    and read by the Smart Ear engine.
    """

    mode: JanusMode = JanusMode.SEMANTIC
    is_streaming: bool = False
    is_recording: bool = False
    emotion_override: EmotionOverride = EmotionOverride.AUTO


# Global-ish shared state (within the backend process)
control_state = ControlState()

# Queues for events emitted by the engine
transcript_queue: "asyncio.Queue[TranscriptMessage]" = asyncio.Queue()
packet_queue: "asyncio.Queue[PacketSummaryMessage]" = asyncio.Queue()
