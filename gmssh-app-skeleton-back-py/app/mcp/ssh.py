"""SSH tool contract used by the MCP server.

The application that owns the SSH session should provide an implementation of
this adapter. The default implementation deliberately refuses to run commands.
"""

from abc import ABC, abstractmethod
from typing import Any


class SshToolAdapter(ABC):
    """Operations that GMSSH can expose as MCP tools."""

    @abstractmethod
    async def exec(self, host: str, command: str, timeout: int = 30) -> dict[str, Any]:
        """Execute a command through an existing, authorized SSH session."""

    async def connect(self, host: str) -> dict[str, Any]:
        raise NotImplementedError("ssh_connect is not configured")

    async def disconnect(self, host: str) -> dict[str, Any]:
        raise NotImplementedError("ssh_disconnect is not configured")

    async def list_sessions(self) -> list[dict[str, Any]]:
        raise NotImplementedError("ssh_list_sessions is not configured")


class DisabledSshToolAdapter(SshToolAdapter):
    """Safe default until GMSSH injects its real SSH session manager."""

    async def exec(self, host: str, command: str, timeout: int = 30) -> dict[str, Any]:
        raise PermissionError("SSH tools are disabled: configure an authorized SshToolAdapter")