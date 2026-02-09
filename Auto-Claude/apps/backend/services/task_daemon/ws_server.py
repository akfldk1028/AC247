"""
WebSocket Server for Real-Time Daemon↔UI Communication
=======================================================

Provides sub-second event delivery from daemon to UI, replacing
the 10-second file polling approach (OpenClaw pattern).

Architecture:
- Runs in a separate thread with its own asyncio event loop
- Broadcasts JSON messages to all connected WebSocket clients
- Graceful fallback: file polling continues alongside WebSocket
- Port written to daemon_status.json for UI auto-discovery

Usage:
    server = DaemonWSServer(port=18800)
    server.start()  # Non-blocking, runs in background thread

    server.broadcast({"type": "task_started", "taskId": "spec-001"})

    server.stop()   # Graceful shutdown
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Default port range for daemon WebSocket server
DEFAULT_WS_PORT = 18800
MAX_PORT_ATTEMPTS = 10  # Try ports 18800-18809


class DaemonWSServer:
    """WebSocket server for real-time daemon status broadcasting."""

    def __init__(self, port: int = DEFAULT_WS_PORT, host: str = "127.0.0.1"):
        self.host = host
        self.port = port
        self.actual_port: int | None = None  # Set after successful bind
        self._clients: set = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server = None
        self._running = False

    def start(self) -> bool:
        """Start the WebSocket server in a background thread.

        Returns:
            True if server started successfully, False otherwise.
        """
        try:
            import websockets  # noqa: F401
        except ImportError:
            logger.warning("websockets package not installed, WS server disabled")
            return False

        self._thread = threading.Thread(
            target=self._run_server,
            name="DaemonWSServer",
            daemon=True,
        )
        self._thread.start()

        # Wait briefly for server to bind
        for _ in range(20):  # 2 seconds max
            if self._running:
                return True
            threading.Event().wait(0.1)

        logger.warning("WebSocket server failed to start within 2s")
        return False

    def _run_server(self) -> None:
        """Run the asyncio event loop for the WebSocket server."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        """Start serving WebSocket connections, trying multiple ports."""
        import websockets

        for attempt in range(MAX_PORT_ATTEMPTS):
            port = self.port + attempt
            try:
                self._server = await websockets.serve(
                    self._handler,
                    self.host,
                    port,
                )
                self.actual_port = port
                self._running = True
                logger.info(f"WebSocket server listening on ws://{self.host}:{port}")

                # Block until server is closed
                await self._server.wait_closed()
                return

            except OSError as e:
                if "address already in use" in str(e).lower() or getattr(e, 'errno', 0) == 10048:
                    logger.debug(f"Port {port} in use, trying next...")
                    continue
                raise

        logger.error(f"Could not bind WebSocket server (tried ports {self.port}-{self.port + MAX_PORT_ATTEMPTS - 1})")

    async def _handler(self, websocket) -> None:
        """Handle a single WebSocket connection."""
        self._clients.add(websocket)
        remote = getattr(websocket, 'remote_address', 'unknown')
        logger.info(f"WebSocket client connected: {remote}")
        try:
            async for message in websocket:
                # Client→daemon messages (future: commands like pause/resume)
                logger.debug(f"Received from client: {message[:200]}")
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info(f"WebSocket client disconnected: {remote}")

    def broadcast(self, data: dict[str, Any]) -> None:
        """Broadcast a JSON message to all connected clients.

        Thread-safe: can be called from any thread.
        """
        if not self._running or not self._clients or not self._loop:
            return

        message = json.dumps(data, default=str)

        async def _send_all():
            disconnected = set()
            for client in list(self._clients):
                try:
                    await client.send(message)
                except Exception:
                    disconnected.add(client)
            self._clients -= disconnected

        try:
            asyncio.run_coroutine_threadsafe(_send_all(), self._loop)
        except RuntimeError:
            pass  # Event loop closed

    def broadcast_status(self, status: dict[str, Any]) -> None:
        """Broadcast full daemon status to all clients.

        Wraps the status dict in a standard envelope.
        """
        self.broadcast({
            "type": "daemon_status",
            "data": status,
        })

    def broadcast_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Broadcast a typed event to all clients.

        Args:
            event_type: e.g., 'task_started', 'task_completed', 'task_queued'
            payload: Optional event-specific data
        """
        msg: dict[str, Any] = {"type": event_type}
        if payload:
            msg["data"] = payload
        self.broadcast(msg)

    @property
    def client_count(self) -> int:
        """Number of currently connected WebSocket clients."""
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        """Whether the server is actively accepting connections."""
        return self._running

    def stop(self) -> None:
        """Stop the WebSocket server gracefully."""
        if not self._running:
            return

        self._running = False

        if self._server and self._loop:
            async def _close():
                self._server.close()
                await self._server.wait_closed()

            try:
                future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
                future.result(timeout=5)
            except Exception:
                pass

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("WebSocket server stopped")
