"""MCP stdio server for use by desktop agents and local MCP hosts."""

import asyncio
import json
import sys
from typing import Any

from app.mcp.registry import McpToolRegistry


def _response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        response["result"] = result
    else:
        response["error"] = error
    return response


async def handle_message(message: dict[str, Any], registry: McpToolRegistry) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None and method and method.startswith("notifications/"):
        return None
    if method == "initialize":
        return _response(request_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "gmssh", "version": "0.1.0"},
        })
    if method == "tools/list":
        return _response(request_id, {"tools": registry.list_tools()})
    if method == "tools/call":
        params = message.get("params") or {}
        try:
            result = await registry.call(params["name"], params.get("arguments") or {})
            return _response(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=True)}], "structuredContent": result})
        except (KeyError, NotImplementedError, PermissionError, ValueError) as exc:
            return _response(request_id, error={"code": -32602, "message": str(exc)})
    return _response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


async def serve(registry: McpToolRegistry | None = None) -> None:
    tool_registry = registry or McpToolRegistry()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = await handle_message(json.loads(line), tool_registry)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(serve())