"""Filesystem MCP tool — sandboxed local file operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent.models import ToolResult

from .base import MCPTool


class FilesystemTool(MCPTool):
    """MCP tool for sandboxed filesystem operations."""

    def __init__(self, sandbox_root: str = "/tmp/agent-workspace"):
        self._root = Path(sandbox_root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Read, write, list, and delete files in a sandboxed workspace"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "delete", "mkdir"],
                },
                "path": {"type": "string", "description": "Relative path within sandbox"},
                "content": {"type": "string", "description": "Content to write (for write action)"},
            },
            "required": ["action", "path"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        action = params.get("action", "")
        rel_path = params.get("path", "")

        # Sandbox enforcement — resolve and check prefix
        target = (self._root / rel_path).resolve()
        if not str(target).startswith(str(self._root.resolve())):
            return ToolResult(success=False, error="Path escapes sandbox")

        try:
            if action == "read":
                return self._read(target)
            elif action == "write":
                return self._write(target, params.get("content", ""))
            elif action == "list":
                return self._list(target)
            elif action == "delete":
                return self._delete(target)
            elif action == "mkdir":
                return self._mkdir(target)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _read(self, path: Path) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path.name}")
        content = path.read_text(encoding="utf-8")
        return ToolResult(success=True, output={"content": content, "size": len(content)})

    def _write(self, path: Path, content: str) -> ToolResult:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output={"path": str(path.name), "size": len(content)})

    def _list(self, path: Path) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error=f"Directory not found: {path.name}")
        entries = []
        for entry in sorted(path.iterdir()):
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
        return ToolResult(success=True, output=entries)

    def _delete(self, path: Path) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error=f"Not found: {path.name}")
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()
        return ToolResult(success=True, output={"deleted": path.name})

    def _mkdir(self, path: Path) -> ToolResult:
        path.mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, output={"created": str(path.name)})
