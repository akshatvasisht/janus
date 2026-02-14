"""
WebSocket manager for bi-directional communication with frontend.

Handles WebSocket connections, receives control messages from the frontend,
and forwards transcript and packet summary events from the engine to the frontend.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..common import engine_state
from .types import ControlMessage, JanusOutboundMessage, ControlStateMessage

router = APIRouter()


@router.websocket("/ws/janus")
async def janus_ws(websocket: WebSocket) -> None:
    """
    Bi-directional WebSocket for Janus.
    
    Receives ControlMessage from frontend and updates engine_state.control_state.
    Sends TranscriptMessage and PacketSummaryMessage from engine queues.
    
    Args:
        websocket: WebSocket connection instance.
    
    Returns:
        None
    """
    await websocket.accept()

    # Send initial state to sync UI
    state = engine_state.control_state
    initial_state = ControlStateMessage(
        type="control_state",
        is_streaming=state.is_streaming,
        is_recording=state.is_recording,
        mode=state.mode,
        emotion_override=state.emotion_override,
    )
    await _send_event(websocket, initial_state)

    recv_task = asyncio.create_task(_recv_loop(websocket))
    send_task = asyncio.create_task(_send_loop(websocket))

    try:
        done, pending = await asyncio.wait(
            [recv_task, send_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        for task in done:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"Task failed: {e}")

    except Exception as e:
        print(f"WebSocket handler error: {e}")
    finally:
        _reset_control_state()
        recv_task.cancel()
        send_task.cancel()


def _reset_control_state() -> None:
    """
    Reset engine_state.control_state to idle values.
    """
    state = engine_state.control_state
    state.is_streaming = False
    state.is_recording = False
    state.is_talking = False
    print(f"Control State Reset on Disconnect: {state}")


async def _recv_loop(websocket: WebSocket) -> None:
    """
    Receive ControlMessage payloads from frontend and update control_state.
    
    Args:
        websocket: WebSocket connection instance.
    
    Returns:
        None
    """
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "control":
                msg = ControlMessage(**data)
                _apply_control_message(msg)
    except WebSocketDisconnect:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in recv loop: {e}")


def _apply_control_message(msg: ControlMessage) -> None:
    """
    Update engine_state.control_state with non-None fields from a ControlMessage.
    
    Args:
        msg: ControlMessage containing state updates.
    
    Returns:
        None
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
    
    Args:
        websocket: WebSocket connection instance.
    
    Returns:
        None
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
    
    Args:
        websocket: WebSocket connection instance.
        event: Outbound message to send.
    
    Returns:
        None
    """
    await websocket.send_text(event.model_dump_json())
