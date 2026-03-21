"""WebSocket connection manager for real-time updates."""

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """
    Manages WebSocket connections for real-time job updates.

    Supports:
    - Multiple clients per job
    - Broadcasting to all clients watching a job
    - Graceful disconnection handling
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        # Map of job_id -> set of WebSocket connections
        self._job_connections: dict[int, set[WebSocket]] = {}
        # Map of WebSocket -> set of job_ids being watched
        self._client_jobs: dict[WebSocket, set[int]] = {}
        # All active connections (for global broadcasts)
        self._active_connections: set[WebSocket] = set()
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket to connect
        """
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
            self._client_jobs[websocket] = set()

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The WebSocket to disconnect
        """
        async with self._lock:
            self._active_connections.discard(websocket)

            # Remove from all job subscriptions
            if websocket in self._client_jobs:
                for job_id in self._client_jobs[websocket]:
                    if job_id in self._job_connections:
                        self._job_connections[job_id].discard(websocket)
                        if not self._job_connections[job_id]:
                            del self._job_connections[job_id]
                del self._client_jobs[websocket]

    async def subscribe_to_job(self, websocket: WebSocket, job_id: int) -> None:
        """
        Subscribe a client to job updates.

        Args:
            websocket: The client WebSocket
            job_id: The job to subscribe to
        """
        async with self._lock:
            if job_id not in self._job_connections:
                self._job_connections[job_id] = set()
            self._job_connections[job_id].add(websocket)

            if websocket in self._client_jobs:
                self._client_jobs[websocket].add(job_id)

    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: int) -> None:
        """
        Unsubscribe a client from job updates.

        Args:
            websocket: The client WebSocket
            job_id: The job to unsubscribe from
        """
        async with self._lock:
            if job_id in self._job_connections:
                self._job_connections[job_id].discard(websocket)
                if not self._job_connections[job_id]:
                    del self._job_connections[job_id]

            if websocket in self._client_jobs:
                self._client_jobs[websocket].discard(job_id)

    async def broadcast_job_update(self, job_id: int, data: dict[str, Any]) -> None:
        """
        Broadcast a job update to all subscribed clients.

        Args:
            job_id: The job ID
            data: The update data to send
        """
        message = json.dumps({"type": "job_update", "job_id": job_id, "data": data})

        async with self._lock:
            connections = self._job_connections.get(job_id, set()).copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_all(self, data: dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            data: The data to broadcast
        """
        message = json.dumps(data)

        async with self._lock:
            connections = self._active_connections.copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """
        Send a message to a specific client.

        Args:
            websocket: The client WebSocket
            data: The data to send
        """
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            await self.disconnect(websocket)

    @property
    def active_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._active_connections)

    def get_job_subscriber_count(self, job_id: int) -> int:
        """Get the number of subscribers for a job."""
        return len(self._job_connections.get(job_id, set()))


# Global connection manager instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
