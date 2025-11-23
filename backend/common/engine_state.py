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
# We initialize them as None and create them on startup to ensure they bind to the correct loop
transcript_queue: Optional[asyncio.Queue] = None
packet_queue: Optional[asyncio.Queue] = None


def get_transcript_queue() -> asyncio.Queue:
    global transcript_queue
    if transcript_queue is None:
        transcript_queue = asyncio.Queue()
    return transcript_queue


def get_packet_queue() -> asyncio.Queue:
    global packet_queue
    if packet_queue is None:
        packet_queue = asyncio.Queue()
    return packet_queue


def reset_queues():
    """Helper for tests to reset queues between runs"""
    global transcript_queue, packet_queue
    transcript_queue = asyncio.Queue()
    packet_queue = asyncio.Queue()
