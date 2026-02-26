"""Demo: Autonomous task execution.

Shows the agent receiving a high-level goal and autonomously:
1. Planning the steps
2. Executing each step with MCP tools
3. Verifying outputs
4. Reporting results

Run:
    uv run python -m demo.autonomous_task
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel

from agent.core import Agent
from agent.executor import Executor
from agent.models import Plan, Step, ToolResult
from agent.planner import Planner
from agent.verifier import Verifier
from safety.guardrails import Guardrails
from tools.code_executor_tool import CodeExecutorTool
from tools.filesystem_tool import FilesystemTool

console = Console()


class DemoPlanner(Planner):
    """A planner that uses pre-defined steps for demo reproducibility.

    In production, this would call the LLM. For the demo, we use
    deterministic steps so the output is always reproducible.
    """

    async def create_plan(self, goal: str, context=None) -> Plan:
        """Create a deterministic demo plan."""
        steps = [
            Step(
                description="Create project directory",
                tool_name="filesystem",
                tool_params={"action": "mkdir", "path": "fibonacci_project"},
            ),
            Step(
                description="Write fibonacci module",
                tool_name="filesystem",
                tool_params={
                    "action": "write",
                    "path": "fibonacci_project/fibonacci.py",
                    "content": '''"""Fibonacci module with multiple implementations."""


def fibonacci_recursive(n: int) -> int:
    """Calculate nth Fibonacci number recursively."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """Calculate nth Fibonacci number iteratively (O(n) time, O(1) space)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_sequence(n: int) -> list[int]:
    """Return first n Fibonacci numbers."""
    if n <= 0:
        return []
    seq = [0]
    if n == 1:
        return seq
    seq.append(1)
    for i in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq
''',
                },
            ),
            Step(
                description="Write test suite",
                tool_name="filesystem",
                tool_params={
                    "action": "write",
                    "path": "fibonacci_project/test_fibonacci.py",
                    "content": '''"""Tests for the fibonacci module."""

import sys
sys.path.insert(0, "/tmp/agent-workspace/fibonacci_project")

from fibonacci import fibonacci_recursive, fibonacci_iterative, fibonacci_sequence


def test_base_cases():
    assert fibonacci_recursive(0) == 0
    assert fibonacci_recursive(1) == 1
    assert fibonacci_iterative(0) == 0
    assert fibonacci_iterative(1) == 1


def test_known_values():
    known = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    for i, expected in enumerate(known):
        assert fibonacci_recursive(i) == expected
        assert fibonacci_iterative(i) == expected


def test_sequence():
    assert fibonacci_sequence(0) == []
    assert fibonacci_sequence(1) == [0]
    assert fibonacci_sequence(5) == [0, 1, 1, 2, 3]
    assert fibonacci_sequence(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_implementations_agree():
    for n in range(20):
        assert fibonacci_recursive(n) == fibonacci_iterative(n)


def test_negative_raises():
    import pytest
    with pytest.raises(ValueError):
        fibonacci_recursive(-1)
    with pytest.raises(ValueError):
        fibonacci_iterative(-1)


if __name__ == "__main__":
    test_base_cases()
    test_known_values()
    test_sequence()
    test_implementations_agree()
    print("All tests passed!")
''',
                },
            ),
            Step(
                description="Run tests to verify correctness",
                tool_name="code_executor",
                tool_params={
                    "code": """import sys
sys.path.insert(0, "/tmp/agent-workspace/fibonacci_project")
from fibonacci import fibonacci_recursive, fibonacci_iterative, fibonacci_sequence

# Run tests
errors = []

# Base cases
for n, expected in [(0, 0), (1, 1)]:
    for fn_name, fn in [("recursive", fibonacci_recursive), ("iterative", fibonacci_iterative)]:
        result = fn(n)
        if result != expected:
            errors.append(f"{fn_name}({n}) = {result}, expected {expected}")

# Known values
known = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
for i, expected in enumerate(known):
    for fn_name, fn in [("recursive", fibonacci_recursive), ("iterative", fibonacci_iterative)]:
        result = fn(i)
        if result != expected:
            errors.append(f"{fn_name}({i}) = {result}, expected {expected}")

# Sequence
seq = fibonacci_sequence(10)
if seq != known:
    errors.append(f"sequence(10) = {seq}, expected {known}")

# Implementations agree
for n in range(20):
    r = fibonacci_recursive(n)
    i = fibonacci_iterative(n)
    if r != i:
        errors.append(f"Mismatch at n={n}: recursive={r}, iterative={i}")

if errors:
    print("FAILURES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"All tests passed! Verified {len(known)} known values + agreement up to n=19")
    print(f"fibonacci(10) = {fibonacci_iterative(10)}")
    print(f"First 10: {fibonacci_sequence(10)}")
""",
                },
            ),
            Step(
                description="Verify output files exist",
                tool_name="filesystem",
                tool_params={"action": "list", "path": "fibonacci_project"},
            ),
        ]

        return Plan(goal=goal, steps=steps)


async def main() -> None:
    """Run the autonomous task demo."""
    console.print(
        Panel(
            "[bold]Rise of AI Agents — Autonomous Task Demo[/]\n\n"
            "This demo shows the agent autonomously:\n"
            "1. Creating a project directory\n"
            "2. Writing a Fibonacci module with multiple implementations\n"
            "3. Writing a comprehensive test suite\n"
            "4. Running tests to verify correctness\n"
            "5. Verifying all output files exist\n\n"
            "All using MCP-compatible tool connectors with safety guardrails.",
            title="🤖 Demo",
            border_style="blue",
        )
    )

    # Set up agent with demo planner (deterministic steps)
    agent = Agent(
        planner=DemoPlanner(),
        executor=Executor(),
        verifier=Verifier.__new__(Verifier),  # Skip OpenAI init for demo
        guardrails=Guardrails(auto_approve_all=True),
    )

    # Patch verifier to not need OpenAI
    from agent.verifier import VerificationResult

    async def mock_verify_step(step, goal):
        if step.result and step.result.success:
            return VerificationResult(passed=True, reason="Tool succeeded")
        return VerificationResult(passed=False, reason="Tool failed", should_retry=True)

    async def mock_verify_plan(goal, steps):
        from agent.models import StepStatus
        succeeded = sum(1 for s in steps if s.status == StepStatus.SUCCESS)
        total = len(steps)
        return VerificationResult(
            passed=succeeded == total,
            reason=f"{succeeded}/{total} steps completed",
        )

    agent.verifier.verify_step = mock_verify_step
    agent.verifier.verify_plan_completion = mock_verify_plan

    # Register tools
    agent.register_tool("filesystem", FilesystemTool())
    agent.register_tool("code_executor", CodeExecutorTool())

    # Run
    goal = "Create a Python fibonacci module with multiple implementations and a test suite, then verify all tests pass"
    state = await agent.run(goal)

    # Print audit summary
    console.print("\n[bold]📊 Audit Trail Summary:[/]")
    for entry in state.audit_trail:
        status = "✅" if (entry.result and entry.result.success) else "❌"
        console.print(
            f"  {status} [{entry.risk_level.value:6s}] {entry.action} "
            f"({entry.tool_name}) — {entry.rationale}"
        )

    console.print(f"\n[bold green]Demo complete![/] {state.completed_steps} steps executed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
