import asyncio

from app.mcp.registry import McpToolRegistry
from app.mcp.stdio import handle_message


def test_initialize_and_list_tools():
    registry = McpToolRegistry()
    initialized = asyncio.run(handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, registry))
    tools = asyncio.run(handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, registry))

    assert initialized["result"]["capabilities"]["tools"] == {}
    assert {tool["name"] for tool in tools["result"]["tools"]} == {
        "ssh_connect", "ssh_disconnect", "ssh_exec", "ssh_list_sessions"
    }


def test_disabled_ssh_tool_returns_protocol_error():
    response = asyncio.run(handle_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "ssh_exec", "arguments": {"host": "demo", "command": "id"}},
    }, McpToolRegistry()))

    assert response["error"]["code"] == -32602
    assert "disabled" in response["error"]["message"]