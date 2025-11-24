"""
WebSocket manager for bi-directional communication with frontend.

Handles WebSocket connections, receives control messages from the frontend,
and forwards transcript and packet summary events from the engine to the frontend.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..common import engine_state
from .types import ControlMessage, JanusOutboundMessage

router = APIRouter()


@router.websocket("/ws/janus")
async def janus_ws(websocket: WebSocket) -> None:
    """
    Bi-directional WebSocket for Janus.
    - Receives ControlMessage from frontend, updates engine_state.control_state
    - Sends TranscriptMessage and PacketSummaryMessage from engine queues
    """
    await websocket.accept()

    recv_task = asyncio.create_task(_recv_loop(websocket))
    send_task = asyncio.create_task(_send_loop(websocket))

    try:
        # Wait for either task to finish (usually recv_loop ends on disconnect)
        done, pending = await asyncio.wait(
            [recv_task, send_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel whichever is still running
        for task in pending:
            task.cancel()

        # Check for exceptions in the done task
        for task in done:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except WebSocketDisconnect:
                # Normal disconnect
                pass
            except Exception as e:
                print(f"Task failed: {e}")

    except Exception as e:
        print(f"WebSocket handler error: {e}")
    finally:
        # Ensure everything is cleaned up
        recv_task.cancel()
        send_task.cancel()


async def _recv_loop(websocket: WebSocket) -> None:
    """
    Receive ControlMessage payloads from frontend and update control_state.
    """
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "control":
                msg = ControlMessage(**data)
                _apply_control_message(msg)
    except WebSocketDisconnect:
        # Normal closure
        raise
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in recv loop: {e}")


def _apply_control_message(msg: ControlMessage) -> None:
    """
    Update engine_state.control_state with non-None fields
    from a ControlMessage.
    """
    state = engine_state.control_state

    if msg.is_streaming is not None:
        state.is_streaming = msg.is_streaming

    if msg.is_recording is not None:
        state.is_recording = msg.is_recording

    if msg.mode is not None:
        state.mode = msg.mode

    if msg.emotion_override is not None:
        state.emotion_override = msg.emotion_override

    print(f"Control State Updated: {state}")


async def _send_loop(websocket: WebSocket) -> None:
    """
    Drain transcript_queue and packet_queue and forward to frontend.
    """
    transcript_queue = engine_state.get_transcript_queue()
    packet_queue = engine_state.get_packet_queue()

    try:
        while True:
            t_task = asyncio.create_task(transcript_queue.get())
            p_task = asyncio.create_task(packet_queue.get())

            done, pending = await asyncio.wait(
                [t_task, p_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                event = task.result()
                await _send_event(websocket, event)

            for task in pending:
                task.cancel()

    except asyncio.CancelledError:
        raise
    except WebSocketDisconnect:
        raise
    except Exception as e:
        print(f"Error in send loop: {e}")


async def _send_event(websocket: WebSocket, event: JanusOutboundMessage) -> None:
    """
    Serialize a Pydantic outbound message to JSON and send over WebSocket.
    """
    await websocket.send_text(event.model_dump_json())
