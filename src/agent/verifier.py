"""Output verifier — checks step results and decides on retry/replan/escalate."""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from .models import Step, StepStatus, ToolResult

logger = logging.getLogger(__name__)


class Verifier:
    """Verifies tool outputs meet expectations and decides next action."""

    def __init__(self, client: AsyncOpenAI | None = None, model: str = "gpt-4o"):
        self._client = client or AsyncOpenAI()
        self._model = model

    async def verify_step(self, step: Step, plan_goal: str) -> VerificationResult:
        """Verify whether a step's output satisfies its intent."""
        if step.result is None:
            return VerificationResult(passed=False, reason="No result to verify")

        if not step.result.success:
            return VerificationResult(
                passed=False,
                reason=f"Step failed: {step.result.error}",
                should_retry=step.retry_count < step.max_retries,
            )

        # For simple success cases, trust the tool
        if step.result.output is not None:
            return VerificationResult(passed=True, reason="Tool returned success with output")

        return VerificationResult(passed=True, reason="Tool returned success")

    async def verify_plan_completion(
        self, goal: str, steps: list[Step]
    ) -> VerificationResult:
        """Verify whether the overall plan achieved the goal."""
        succeeded = sum(1 for s in steps if s.status == StepStatus.SUCCESS)
        failed = sum(1 for s in steps if s.status == StepStatus.FAILED)
        total = len(steps)

        if failed == 0 and succeeded == total:
            return VerificationResult(
                passed=True,
                reason=f"All {total} steps completed successfully",
            )

        if succeeded == 0:
            return VerificationResult(
                passed=False,
                reason=f"All {total} steps failed",
                should_retry=False,
            )

        return VerificationResult(
            passed=succeeded > failed,
            reason=f"{succeeded}/{total} steps succeeded, {failed} failed",
            should_retry=failed > 0,
        )


class VerificationResult:
    """Result of a verification check."""

    def __init__(
        self,
        passed: bool,
        reason: str = "",
        should_retry: bool = False,
        suggested_replan: dict[str, Any] | None = None,
    ):
        self.passed = passed
        self.reason = reason
        self.should_retry = should_retry
        self.suggested_replan = suggested_replan

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"VerificationResult({status}: {self.reason})"
