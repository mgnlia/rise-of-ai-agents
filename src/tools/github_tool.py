"""GitHub MCP tool — interact with GitHub API."""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.models import ToolResult

from .base import MCPTool


class GitHubTool(MCPTool):
    """MCP tool for GitHub operations: create repos, files, issues, read files."""

    def __init__(self, token: str | None = None):
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._base = "https://api.github.com"

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Interact with GitHub: create repos, read/write files, create issues"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_repo", "read_file", "create_file", "create_issue", "list_repos"],
                },
                "owner": {"type": "string"},
                "repo": {"type": "string"},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "private": {"type": "boolean", "default": False},
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        action = params.get("action", "")
        headers = {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            try:
                if action == "create_repo":
                    return await self._create_repo(client, params)
                elif action == "read_file":
                    return await self._read_file(client, params)
                elif action == "create_file":
                    return await self._create_file(client, params)
                elif action == "create_issue":
                    return await self._create_issue(client, params)
                elif action == "list_repos":
                    return await self._list_repos(client, params)
                else:
                    return ToolResult(success=False, error=f"Unknown action: {action}")
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=f"HTTP error: {e}")

    async def _create_repo(self, client: httpx.AsyncClient, params: dict) -> ToolResult:
        resp = await client.post(
            f"{self._base}/user/repos",
            json={
                "name": params.get("repo", ""),
                "private": params.get("private", False),
                "auto_init": True,
            },
        )
        if resp.status_code == 201:
            data = resp.json()
            return ToolResult(success=True, output={"url": data["html_url"], "full_name": data["full_name"]})
        return ToolResult(success=False, error=f"Status {resp.status_code}: {resp.text[:200]}")

    async def _read_file(self, client: httpx.AsyncClient, params: dict) -> ToolResult:
        owner = params.get("owner", "")
        repo = params.get("repo", "")
        path = params.get("path", "")
        resp = await client.get(f"{self._base}/repos/{owner}/{repo}/contents/{path}")
        if resp.status_code == 200:
            import base64
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return ToolResult(success=True, output={"content": content, "sha": data["sha"]})
        return ToolResult(success=False, error=f"Status {resp.status_code}: {resp.text[:200]}")

    async def _create_file(self, client: httpx.AsyncClient, params: dict) -> ToolResult:
        import base64
        owner = params.get("owner", "")
        repo = params.get("repo", "")
        path = params.get("path", "")
        content = base64.b64encode(params.get("content", "").encode()).decode()
        resp = await client.put(
            f"{self._base}/repos/{owner}/{repo}/contents/{path}",
            json={"message": f"Create {path}", "content": content},
        )
        if resp.status_code in (200, 201):
            return ToolResult(success=True, output={"path": path})
        return ToolResult(success=False, error=f"Status {resp.status_code}: {resp.text[:200]}")

    async def _create_issue(self, client: httpx.AsyncClient, params: dict) -> ToolResult:
        owner = params.get("owner", "")
        repo = params.get("repo", "")
        resp = await client.post(
            f"{self._base}/repos/{owner}/{repo}/issues",
            json={"title": params.get("title", ""), "body": params.get("body", "")},
        )
        if resp.status_code == 201:
            data = resp.json()
            return ToolResult(success=True, output={"number": data["number"], "url": data["html_url"]})
        return ToolResult(success=False, error=f"Status {resp.status_code}: {resp.text[:200]}")

    async def _list_repos(self, client: httpx.AsyncClient, params: dict) -> ToolResult:
        resp = await client.get(f"{self._base}/user/repos", params={"per_page": 10, "sort": "updated"})
        if resp.status_code == 200:
            repos = [{"name": r["name"], "url": r["html_url"]} for r in resp.json()]
            return ToolResult(success=True, output=repos)
        return ToolResult(success=False, error=f"Status {resp.status_code}")
