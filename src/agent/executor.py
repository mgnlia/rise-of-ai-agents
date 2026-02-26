"""Step executor — dispatches tool calls and handles retries."""

from __future__ import annotations

import asyncio
import logging
import time

from .models import Step, StepStatus, ToolResult

logger = logging.getLogger(__name__)


class Executor:
    """Executes plan steps by dispatching to registered MCP tools."""

    def __init__(self, tools: dict | None = None):
        self._tools: dict = tools or {}

    def register_tool(self, name: str, tool: object) -> None:
        """Register an MCP tool by name."""
        self._tools[name] = tool

    async def execute_step(self, step: Step) -> ToolResult:
        """Execute a single step, with retry logic."""
        tool = self._tools.get(step.tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {step.tool_name}",
            )

        step.status = StepStatus.RUNNING
        last_error: str | None = None

        for attempt in range(step.max_retries + 1):
            try:
                start = time.monotonic()
                result = await tool.execute(step.tool_params)
                elapsed = (time.monotonic() - start) * 1000
                result.duration_ms = elapsed

                if result.success:
                    step.status = StepStatus.SUCCESS
                    step.result = result
                    logger.info(
                        "Step '%s' succeeded (attempt %d, %.0fms)",
                        step.description,
                        attempt + 1,
                        elapsed,
                    )
                    return result

                last_error = result.error
                step.retry_count = attempt + 1
                logger.warning(
                    "Step '%s' failed (attempt %d): %s",
                    step.description,
                    attempt + 1,
                    result.error,
                )

            except Exception as exc:
                last_error = str(exc)
                step.retry_count = attempt + 1
                logger.error(
                    "Step '%s' exception (attempt %d): %s",
                    step.description,
                    attempt + 1,
                    exc,
                )

            if attempt < step.max_retries:
                delay = min(2**attempt, 10)
                await asyncio.sleep(delay)

        step.status = StepStatus.FAILED
        fail_result = ToolResult(success=False, error=last_error)
        step.result = fail_result
        return fail_result

    async def execute_plan_steps(self, steps: list[Step]) -> list[ToolResult]:
        """Execute steps sequentially, respecting dependencies."""
        results: list[ToolResult] = []
        completed_ids: set[str] = set()

        for step in steps:
            # Check dependencies
            unmet = [d for d in step.depends_on if d not in completed_ids]
            if unmet:
                step.status = StepStatus.SKIPPED
                result = ToolResult(
                    success=False,
                    error=f"Skipped: unmet dependencies {unmet}",
                )
                step.result = result
                results.append(result)
                continue

            result = await self.execute_step(step)
            results.append(result)

            if result.success:
                completed_ids.add(step.id)

        return results
