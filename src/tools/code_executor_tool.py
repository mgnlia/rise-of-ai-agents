"""Code Executor MCP tool — run Python code in a sandboxed subprocess."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from agent.models import ToolResult

from .base import MCPTool


class CodeExecutorTool(MCPTool):
    """MCP tool for executing Python code in a sandboxed subprocess."""

    def __init__(self, timeout_seconds: int = 30, max_output_chars: int = 10000):
        self._timeout = timeout_seconds
        self._max_output = max_output_chars

    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed subprocess and return stdout/stderr"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout_seconds": {"type": "integer", "default": 30},
            },
            "required": ["code"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        code = params.get("code", "")
        timeout = min(params.get("timeout_seconds", self._timeout), self._timeout)

        if not code.strip():
            return ToolResult(success=False, error="No code provided")

        # Write code to a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Resource limits via environment
                env={
                    "PATH": "/usr/bin:/bin",
                    "HOME": "/tmp",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False,
                    error=f"Execution timed out after {timeout}s",
                    metadata={"timeout": True},
                )

            stdout_str = stdout.decode("utf-8", errors="replace")[: self._max_output]
            stderr_str = stderr.decode("utf-8", errors="replace")[: self._max_output]

            return ToolResult(
                success=proc.returncode == 0,
                output={
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "returncode": proc.returncode,
                },
                error=stderr_str if proc.returncode != 0 else None,
            )

        finally:
            Path(script_path).unlink(missing_ok=True)
