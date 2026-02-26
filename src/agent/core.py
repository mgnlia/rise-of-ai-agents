"""Core agent loop — plan, execute, verify, report."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .executor import Executor
from .models import (
    ActionRisk,
    AgentState,
    ApprovalDecision,
    AuditEntry,
    StepStatus,
    ToolResult,
)
from .planner import Planner
from .verifier import Verifier

logger = logging.getLogger(__name__)
console = Console()


class Agent:
    """Autonomous AI agent that plans, executes, verifies, and reports.

    Usage:
        agent = Agent()
        agent.register_tool("github", GitHubTool())
        result = await agent.run("Create a fibonacci module with tests")
    """

    def __init__(
        self,
        planner: Planner | None = None,
        executor: Executor | None = None,
        verifier: Verifier | None = None,
        guardrails: Any | None = None,
        max_steps: int = 20,
        timeout_seconds: int = 300,
    ):
        self.planner = planner or Planner()
        self.executor = executor or Executor()
        self.verifier = verifier or Verifier()
        self.guardrails = guardrails
        self._max_steps = max_steps
        self._timeout = timeout_seconds

    def register_tool(self, name: str, tool: object) -> None:
        """Register an MCP tool with the executor."""
        self.executor.register_tool(name, tool)

    async def run(self, goal: str, context: dict[str, Any] | None = None) -> AgentState:
        """Execute the full agent loop for a given goal."""
        state = AgentState(
            goal=goal,
            max_steps=self._max_steps,
            timeout_seconds=self._timeout,
        )

        console.print(Panel(f"[bold blue]Goal:[/] {goal}", title="🤖 Agent Started"))

        # Phase 1: Plan
        console.print("\n[bold yellow]📋 Phase 1: Planning...[/]")
        plan = await self.planner.create_plan(goal, context)
        state.plan = plan

        self._print_plan(plan)

        if not plan.steps:
            console.print("[red]No steps generated. Aborting.[/]")
            state.finished_at = datetime.now(timezone.utc)
            return state

        # Phase 2: Execute
        console.print("\n[bold yellow]⚡ Phase 2: Executing...[/]")
        for i, step in enumerate(plan.steps):
            if i >= self._max_steps:
                console.print(f"[red]Max steps ({self._max_steps}) reached. Stopping.[/]")
                break

            state.current_step_index = i
            console.print(f"\n  [cyan]Step {i + 1}/{len(plan.steps)}:[/] {step.description}")

            # Guardrails check
            if self.guardrails:
                decision = self.guardrails.check_action(step.tool_name, step.tool_params)
                if decision == ApprovalDecision.DENY:
                    console.print(f"  [red]⛔ Denied by guardrails[/]")
                    step.status = StepStatus.SKIPPED
                    state.audit_trail.append(
                        AuditEntry(
                            action=step.description,
                            tool_name=step.tool_name,
                            tool_params=step.tool_params,
                            decision=ApprovalDecision.DENY,
                            rationale="Blocked by guardrail policy",
                        )
                    )
                    continue
                elif decision == ApprovalDecision.REQUIRE_APPROVAL:
                    console.print(f"  [yellow]⚠️  Requires human approval (auto-approving in demo)[/]")

            # Execute
            result = await self.executor.execute_step(step)

            # Audit
            risk = self._assess_risk(step.tool_name, step.tool_params)
            state.audit_trail.append(
                AuditEntry(
                    action=step.description,
                    tool_name=step.tool_name,
                    tool_params=step.tool_params,
                    result=result,
                    risk_level=risk,
                    decision=ApprovalDecision.AUTO_APPROVE,
                    rationale="Executed successfully" if result.success else f"Failed: {result.error}",
                )
            )

            if result.success:
                state.completed_steps += 1
                console.print(f"  [green]✅ Success[/] ({result.duration_ms:.0f}ms)")
            else:
                state.failed_steps += 1
                console.print(f"  [red]❌ Failed: {result.error}[/]")

            # Phase 3: Verify
            verification = await self.verifier.verify_step(step, goal)
            if not verification.passed and verification.should_retry:
                console.print(f"  [yellow]🔄 Verification failed, will retry in next cycle[/]")

        # Final verification
        console.print("\n[bold yellow]🔍 Phase 3: Verifying...[/]")
        final = await self.verifier.verify_plan_completion(goal, plan.steps)

        state.finished_at = datetime.now(timezone.utc)

        # Phase 4: Report
        self._print_report(state, final)

        return state

    def _assess_risk(self, tool_name: str, params: dict) -> ActionRisk:
        """Assess the risk level of a tool action."""
        high_risk_tools = {"code_executor"}
        medium_risk_actions = {"write", "delete", "create_repo", "create_file"}

        if tool_name in high_risk_tools:
            return ActionRisk.HIGH

        action = params.get("action", "")
        if action in medium_risk_actions:
            return ActionRisk.MEDIUM

        return ActionRisk.LOW

    def _print_plan(self, plan: Any) -> None:
        """Pretty-print the execution plan."""
        table = Table(title="Execution Plan", show_lines=True)
        table.add_column("#", style="bold", width=4)
        table.add_column("Step", style="cyan")
        table.add_column("Tool", style="green")

        for i, step in enumerate(plan.steps, 1):
            table.add_row(str(i), step.description, step.tool_name)

        console.print(table)

    def _print_report(self, state: AgentState, verification: Any) -> None:
        """Print the final execution report."""
        duration = "N/A"
        if state.finished_at and state.started_at:
            delta = state.finished_at - state.started_at
            duration = f"{delta.total_seconds():.1f}s"

        status = "[green]✅ COMPLETED" if verification.passed else "[red]❌ INCOMPLETE"

        report = Table(title="Execution Report", show_lines=True)
        report.add_column("Metric", style="bold")
        report.add_column("Value")

        report.add_row("Goal", state.goal)
        report.add_row("Status", status)
        report.add_row("Duration", duration)
        report.add_row("Steps Completed", f"{state.completed_steps}/{len(state.plan.steps) if state.plan else 0}")
        report.add_row("Steps Failed", str(state.failed_steps))
        report.add_row("Audit Entries", str(len(state.audit_trail)))
        report.add_row("Verification", verification.reason)

        console.print("\n")
        console.print(report)
