"""Web Search MCP tool — search the web and return structured results."""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.models import ToolResult

from .base import MCPTool


class WebSearchTool(MCPTool):
    """MCP tool for web search using DuckDuckGo Instant Answer API (no key required)."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web and return structured results"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        max_results = params.get("max_results", 5)

        if not query:
            return ToolResult(success=False, error="Query is required")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                )

                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Search failed: HTTP {resp.status_code}")

                data = resp.json()
                results = []

                # Abstract (direct answer)
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", ""),
                        "snippet": data["Abstract"],
                        "url": data.get("AbstractURL", ""),
                        "source": data.get("AbstractSource", ""),
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                        })

                if not results:
                    return ToolResult(
                        success=True,
                        output={"results": [], "message": "No results found"},
                    )

                return ToolResult(
                    success=True,
                    output={"results": results[:max_results], "query": query},
                )

        except httpx.HTTPError as e:
            return ToolResult(success=False, error=f"HTTP error: {e}")
