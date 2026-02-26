"""Task decomposition planner using LLM."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from .models import Plan, Step

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a task planner for an autonomous AI agent. Given a high-level goal, 
decompose it into concrete, ordered steps. Each step must specify:
- description: what the step does
- tool_name: which tool to use (github, filesystem, web_search, code_executor)
- tool_params: parameters for the tool call

Available tools:
- github: Actions on GitHub (create_repo, create_file, read_file, create_issue). Params: action, owner, repo, path, content, title, body
- filesystem: Local file operations (read, write, list, delete). Params: action, path, content
- web_search: Search the web. Params: query, max_results
- code_executor: Run Python code in sandbox. Params: code, timeout_seconds

Return a JSON array of steps. Each step: {"description": "...", "tool_name": "...", "tool_params": {...}}
Return ONLY the JSON array, no markdown fences or explanation."""


class Planner:
    """Decomposes high-level goals into executable step plans."""

    def __init__(self, client: AsyncOpenAI | None = None, model: str = "gpt-4o"):
        self._client = client or AsyncOpenAI()
        self._model = model

    async def create_plan(self, goal: str, context: dict[str, Any] | None = None) -> Plan:
        """Create an execution plan for the given goal."""
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(goal, context)},
        ]

        logger.info("Planning for goal: %s", goal)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content or "[]"
        steps = self._parse_steps(raw)

        plan = Plan(goal=goal, steps=steps)
        logger.info("Created plan with %d steps", len(steps))
        return plan

    def _build_prompt(self, goal: str, context: dict[str, Any] | None) -> str:
        prompt = f"Goal: {goal}"
        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"
        return prompt

    def _parse_steps(self, raw: str) -> list[Step]:
        """Parse LLM output into Step objects."""
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Failed to parse planner output: %s", raw[:200])
            return []

        steps: list[Step] = []
        for item in data:
            if isinstance(item, dict):
                steps.append(
                    Step(
                        description=item.get("description", "Unknown step"),
                        tool_name=item.get("tool_name", "unknown"),
                        tool_params=item.get("tool_params", {}),
                    )
                )
        return steps
