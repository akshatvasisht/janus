from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel

class JanusMode(str, Enum):
    SEMANTIC = "semantic"  # text + prosody (default)
    TEXT_ONLY = "text_only"  # text only
    MORSE = "morse"  # stretch goal

class EmotionOverride(str, Enum):
    AUTO = "auto"
    CALM = "calm"
    URGENT = "urgent"

class ControlMessage(BaseModel):
    """
    Message sent FROM frontend TO backend over WebSocket.
    Any field that is None == "no change".
    """
    type: Literal["control"]
    is_streaming: Optional[bool] = None
    is_recording: Optional[bool] = None
    mode: Optional[JanusMode] = None
    emotion_override: Optional[EmotionOverride] = None

class TranscriptMessage(BaseModel):
    """
    Message sent FROM backend TO frontend with transcript + prosody.
    """
    type: Literal["transcript"]
    text: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    avg_pitch_hz: Optional[float] = None
    avg_energy: Optional[float] = None

class PacketSummaryMessage(BaseModel):
    """
    Message sent FROM backend TO frontend with "packet" info
    (for bandwidth / cost visualizations).
    """
    type: Literal["packet_summary"]
    bytes: int
    mode: JanusMode
    created_at_ms: int

# Union type for outbound messages
JanusOutboundMessage = TranscriptMessage | PacketSummaryMessage

