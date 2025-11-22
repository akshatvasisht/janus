from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

from .types import ControlMessage, JanusOutboundMessage
from ..common import engine_state

router = APIRouter()

@router.websocket("/ws/janus")
async def janus_ws(websocket: WebSocket):
    """
    Bi-directional WebSocket for Janus.
    - Receives ControlMessage from frontend, updates engine_state.control_state
    - Sends TranscriptMessage and PacketSummaryMessage from engine queues
    """
    await websocket.accept()

    recv_task = asyncio.create_task(_recv_loop(websocket))
    send_task = asyncio.create_task(_send_loop(websocket))

    try:
        await asyncio.gather(recv_task, send_task)
    except WebSocketDisconnect:
        recv_task.cancel()
        send_task.cancel()
    except Exception as e:
        print(f"WebSocket error: {e}")
        recv_task.cancel()
        send_task.cancel()

async def _recv_loop(websocket: WebSocket):
    """
    Receive ControlMessage payloads from frontend and update control_state.
    """
    while True:
        try:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            # Simple type switch on 'type' field
            if data.get("type") == "control":
                msg = ControlMessage(**data)
                _apply_control_message(msg)
            else:
                pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in recv loop: {e}")
            # Optional: break or continue depending on severity
            break

def _apply_control_message(msg: ControlMessage):
    """
    Update engine_state.control_state with non-None fields
    from a ControlMessage.
    """
    state = engine_state.control_state

    # NOTE: These are in-place updates for a shared state object.
    if msg.is_streaming is not None:
        state.is_streaming = msg.is_streaming

    if msg.is_recording is not None:
        state.is_recording = msg.is_recording

    if msg.mode is not None:
        state.mode = msg.mode

    if msg.emotion_override is not None:
        state.emotion_override = msg.emotion_override
        
    print(f"Control State Updated: {state}")

async def _send_loop(websocket: WebSocket):
    """
    Drain transcript_queue and packet_queue and forward to frontend.
    """
    transcript_queue = engine_state.transcript_queue
    packet_queue = engine_state.packet_queue

    while True:
        try:
            # Wait for whichever queue yields first
            # We create tasks for getting from queues. 
            # Note: asyncio.wait with FIRST_COMPLETED is good, but we need to be careful 
            # not to lose items if both are ready.
            
            # Better approach for "race": create tasks, wait for one.
            # But queues don't support "peek". 
            # Use a slightly different pattern: multiple consumers pushing to one websocket is hard 
            # if not synchronized. 
            
            # Simple robust way: loop with small sleep or use asyncio.wait on the .get() coroutines.
            
            t_task = asyncio.create_task(transcript_queue.get())
            p_task = asyncio.create_task(packet_queue.get())
            
            done, pending = await asyncio.wait(
                [t_task, p_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                event = task.result() # Pydantic model
                await _send_event(websocket, event)
                
                # If it was the transcript queue, the packet queue task is still pending.
                # We must cancel it? No, if we cancel it we lose the item if it was about to pop?
                # Actually, queue.get() is safe to cancel if it hasn't returned yet.
                
            # Cancel pending tasks to restart the race cleanly
            for task in pending:
                task.cancel()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in send loop: {e}")
            break

async def _send_event(websocket: WebSocket, event: JanusOutboundMessage):
    """
    Serialize a Pydantic outbound message to JSON and send over WebSocket.
    """
    await websocket.send_text(event.model_dump_json())

