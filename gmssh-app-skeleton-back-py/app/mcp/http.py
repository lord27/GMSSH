"""Minimal MCP SSE transport for the GMSSH plugin process.

Run with ``python -m app.mcp.http``. The transport is intentionally separate
from the Unix-socket plugin RPC server and can be enabled on a private port.
"""

import asyncio
import json
import os
import queue
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.mcp.registry import McpToolRegistry
from app.mcp.stdio import handle_message

_sessions: dict[str, queue.Queue[dict[str, Any]]] = {}
_sessions_lock = threading.Lock()


def _create_session() -> tuple[str, queue.Queue[dict[str, Any]]]:
    session_id = uuid.uuid4().hex
    events: queue.Queue[dict[str, Any]] = queue.Queue()
    with _sessions_lock:
        _sessions[session_id] = events
    return session_id, events


class McpSseHandler(BaseHTTPRequestHandler):
    server_version = "GMSSH-MCP/0.1"

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/mcp/sse":
            self.send_error(404)
            return
        session_id, events = _create_session()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(f"event: endpoint\ndata: /mcp/message?sessionId={session_id}\n\n".encode())
        self.wfile.flush()
        try:
            while True:
                message = events.get()
                self.wfile.write(f"data: {json.dumps(message, ensure_ascii=True)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with _sessions_lock:
                _sessions.pop(session_id, None)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/mcp/message":
            self.send_error(404)
            return
        session_id = (parse_qs(parsed.query).get("sessionId") or [None])[0]
        with _sessions_lock:
            events = _sessions.get(session_id)
        if events is None:
            self.send_error(404, "Unknown MCP session")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            message = json.loads(self.rfile.read(length))
            response = asyncio.run(handle_message(message, McpToolRegistry(event_sink=events.put)))
            if response is not None:
                events.put(response)
            self.send_response(202)
            self.end_headers()
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or os.getenv("GMSSH_MCP_HOST", "127.0.0.1")
    bind_port = port or int(os.getenv("GMSSH_MCP_PORT", "8765"))
    ThreadingHTTPServer((bind_host, bind_port), McpSseHandler).serve_forever()


if __name__ == "__main__":
    serve()