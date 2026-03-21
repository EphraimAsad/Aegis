"""WebSocket endpoints for real-time updates."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import get_connection_manager

router = APIRouter()


@router.websocket("/jobs")
async def websocket_jobs(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time job updates.

    Protocol:
    - Client sends: {"action": "subscribe", "job_id": 123}
    - Client sends: {"action": "unsubscribe", "job_id": 123}
    - Client sends: {"action": "subscribe_all"}
    - Server sends: {"type": "job_update", "job_id": 123, "data": {...}}
    - Server sends: {"type": "connected", "message": "..."}
    """
    manager = get_connection_manager()
    await manager.connect(websocket)

    # Send connection confirmation
    await manager.send_personal(
        websocket,
        {
            "type": "connected",
            "message": "Connected to job updates stream",
        },
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.subscribe_to_job(websocket, int(job_id))
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "subscribed",
                                "job_id": job_id,
                                "message": f"Subscribed to job {job_id}",
                            },
                        )

                elif action == "unsubscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.unsubscribe_from_job(websocket, int(job_id))
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "unsubscribed",
                                "job_id": job_id,
                                "message": f"Unsubscribed from job {job_id}",
                            },
                        )

                elif action == "ping":
                    await manager.send_personal(
                        websocket,
                        {"type": "pong"},
                    )

            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                    },
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


async def broadcast_job_progress(
    job_id: int,
    status: str,
    progress: float,
    message: str | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    """
    Broadcast a job progress update to all subscribers.

    This function should be called from job processing code
    to push real-time updates to connected clients.

    Args:
        job_id: The job ID
        status: Current job status
        progress: Progress percentage (0-100)
        message: Optional progress message
        result: Optional result data (for completed jobs)
    """
    manager = get_connection_manager()

    data = {
        "status": status,
        "progress": progress,
    }

    if message:
        data["message"] = message

    if result:
        data["result"] = result

    await manager.broadcast_job_update(job_id, data)
