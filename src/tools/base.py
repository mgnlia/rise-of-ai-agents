"""Base class for MCP-compatible tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent.models import ToolResult


class MCPTool(ABC):
    """Abstract base class for Model Context Protocol tools.

    Each tool exposes:
    - name: unique identifier
    - description: human-readable description
    - input_schema: JSON Schema describing accepted parameters
    - execute(): async method that performs the action
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's input parameters."""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with the given parameters."""
        ...

    def to_mcp_descriptor(self) -> dict[str, Any]:
        """Return MCP-compatible tool descriptor."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
