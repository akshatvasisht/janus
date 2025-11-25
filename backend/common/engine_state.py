"""
Shared engine state management.

Provides global control state and event queues for communication between
the WebSocket handlers and the Smart Ear engine loop.
"""

import asyncio
from typing import Optional

from pydantic import BaseModel

from ..api.types import (
    EmotionOverride,
    JanusMode,
    PacketSummaryMessage,
    TranscriptMessage,
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
transcript_queue: Optional[asyncio.Queue] = None
packet_queue: Optional[asyncio.Queue] = None


def get_transcript_queue() -> asyncio.Queue:
    """
    Get or create the transcript queue for emitting transcript messages.
    
    Returns:
        asyncio.Queue: Queue for transcript messages.
    """
    global transcript_queue
    if transcript_queue is None:
        transcript_queue = asyncio.Queue()
    return transcript_queue


def get_packet_queue() -> asyncio.Queue:
    """
    Get or create the packet queue for emitting packet summary messages.
    
    Returns:
        asyncio.Queue: Queue for packet summary messages.
    """
    global packet_queue
    if packet_queue is None:
        packet_queue = asyncio.Queue()
    return packet_queue


def reset_queues() -> None:
    """
    Reset queues for testing purposes.
    
    Returns:
        None
    """
    global transcript_queue, packet_queue
    transcript_queue = asyncio.Queue()
    packet_queue = asyncio.Queue()
