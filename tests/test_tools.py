"""Tests for MCP tool connectors."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.models import ToolResult
from tools.filesystem_tool import FilesystemTool
from tools.code_executor_tool import CodeExecutorTool


class TestFilesystemTool:
    @pytest.fixture
    def tool(self, tmp_path):
        return FilesystemTool(sandbox_root=str(tmp_path))

    @pytest.mark.asyncio
    async def test_mcp_descriptor(self, tool):
        desc = tool.to_mcp_descriptor()
        assert desc["name"] == "filesystem"
        assert "inputSchema" in desc
        assert desc["inputSchema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_write_and_read(self, tool):
        # Write
        result = await tool.execute({"action": "write", "path": "hello.txt", "content": "hello world"})
        assert result.success is True

        # Read
        result = await tool.execute({"action": "read", "path": "hello.txt"})
        assert result.success is True
        assert result.output["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_list_directory(self, tool):
        await tool.execute({"action": "write", "path": "a.txt", "content": "a"})
        await tool.execute({"action": "write", "path": "b.txt", "content": "b"})

        result = await tool.execute({"action": "list", "path": "."})
        assert result.success is True
        names = [e["name"] for e in result.output]
        assert "a.txt" in names
        assert "b.txt" in names

    @pytest.mark.asyncio
    async def test_mkdir(self, tool):
        result = await tool.execute({"action": "mkdir", "path": "subdir/nested"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete(self, tool):
        await tool.execute({"action": "write", "path": "deleteme.txt", "content": "temp"})
        result = await tool.execute({"action": "delete", "path": "deleteme.txt"})
        assert result.success is True

        # Verify deleted
        result = await tool.execute({"action": "read", "path": "deleteme.txt"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tool):
        result = await tool.execute({"action": "read", "path": "nope.txt"})
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_sandbox_escape_blocked(self, tool):
        result = await tool.execute({"action": "read", "path": "../../etc/passwd"})
        assert result.success is False
        assert "sandbox" in result.error.lower()

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute({"action": "explode", "path": "x"})
        assert result.success is False


class TestCodeExecutorTool:
    @pytest.fixture
    def tool(self):
        return CodeExecutorTool(timeout_seconds=10)

    @pytest.mark.asyncio
    async def test_mcp_descriptor(self, tool):
        desc = tool.to_mcp_descriptor()
        assert desc["name"] == "code_executor"

    @pytest.mark.asyncio
    async def test_simple_execution(self, tool):
        result = await tool.execute({"code": "print('hello')"})
        assert result.success is True
        assert "hello" in result.output["stdout"]

    @pytest.mark.asyncio
    async def test_execution_error(self, tool):
        result = await tool.execute({"code": "raise ValueError('boom')"})
        assert result.success is False
        assert "boom" in (result.error or "")

    @pytest.mark.asyncio
    async def test_empty_code(self, tool):
        result = await tool.execute({"code": ""})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_timeout(self, tool):
        tool._timeout = 2
        result = await tool.execute({
            "code": "import time; time.sleep(10)",
            "timeout_seconds": 2,
        })
        assert result.success is False
        assert "timeout" in (result.error or "").lower()
