"""Small MCP tool registry independent of the transport."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.mcp.ssh import DisabledSshToolAdapter, SshToolAdapter

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]
EventSink = Callable[[dict[str, Any]], None]


class McpToolRegistry:
    def __init__(self, ssh: SshToolAdapter | None = None, event_sink: EventSink | None = None) -> None:
        self.ssh = ssh or DisabledSshToolAdapter()
        self.event_sink = event_sink
        self._tools: dict[str, tuple[dict[str, Any], ToolHandler]] = {
            "ssh_exec": (
                {
                    "name": "ssh_exec",
                    "description": "Execute a command in an authorized GMSSH SSH session.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "host": {"type": "string"},
                            "command": {"type": "string"},
                            "timeout": {"type": "integer", "minimum": 1, "maximum": 300, "default": 30},
                        },
                        "required": ["host", "command"],
                        "additionalProperties": False,
                    },
                },
                self._ssh_exec,
            ),
            "ssh_connect": (
                {
                    "name": "ssh_connect",
                    "description": "Open or reuse an authorized GMSSH SSH session.",
                    "inputSchema": {"type": "object", "properties": {"host": {"type": "string"}}, "required": ["host"]},
                },
                self._ssh_connect,
            ),
            "ssh_disconnect": (
                {
                    "name": "ssh_disconnect",
                    "description": "Close a GMSSH SSH session.",
                    "inputSchema": {"type": "object", "properties": {"host": {"type": "string"}}, "required": ["host"]},
                },
                self._ssh_disconnect,
            ),
            "ssh_list_sessions": (
                {
                    "name": "ssh_list_sessions",
                    "description": "List SSH sessions available to the current GMSSH user.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                self._ssh_list_sessions,
            ),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [definition for definition, _ in self._tools.values()]

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown MCP tool: {name}")
        self._emit({"type": "tool_call", "tool": name, "arguments": arguments})
        try:
            result = await tool[1](arguments)
        except Exception as exc:
            self._emit({"type": "tool_error", "tool": name, "error": str(exc)})
            raise
        self._emit({"type": "tool_result", "tool": name, "result": result})
        return result

    def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink:
            self.event_sink(event)

    async def _ssh_exec(self, arguments: dict[str, Any]) -> Any:
        return await self.ssh.exec(arguments["host"], arguments["command"], arguments.get("timeout", 30))

    async def _ssh_connect(self, arguments: dict[str, Any]) -> Any:
        return await self.ssh.connect(arguments["host"])

    async def _ssh_disconnect(self, arguments: dict[str, Any]) -> Any:
        return await self.ssh.disconnect(arguments["host"])

    async def _ssh_list_sessions(self, arguments: dict[str, Any]) -> Any:
        return await self.ssh.list_sessions()