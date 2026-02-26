"""Tests for the core agent module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.models import (
    AgentState,
    AuditEntry,
    Plan,
    Step,
    StepStatus,
    ToolResult,
    ActionRisk,
    ApprovalDecision,
)


class TestToolResult:
    def test_success_result(self):
        r = ToolResult(success=True, output={"data": 42})
        assert r.success is True
        assert r.output["data"] == 42
        assert r.error is None

    def test_failure_result(self):
        r = ToolResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"

    def test_duration(self):
        r = ToolResult(success=True, duration_ms=150.5)
        assert r.duration_ms == 150.5


class TestStep:
    def test_step_defaults(self):
        s = Step(description="test", tool_name="filesystem", tool_params={"action": "read"})
        assert s.status == StepStatus.PENDING
        assert s.retry_count == 0
        assert s.max_retries == 3
        assert len(s.id) == 12

    def test_step_with_dependencies(self):
        s = Step(
            description="step 2",
            tool_name="github",
            tool_params={},
            depends_on=["abc123"],
        )
        assert s.depends_on == ["abc123"]


class TestPlan:
    def test_empty_plan(self):
        p = Plan(goal="do something")
        assert p.goal == "do something"
        assert p.steps == []
        assert p.created_at is not None

    def test_plan_with_steps(self):
        steps = [
            Step(description="s1", tool_name="fs", tool_params={}),
            Step(description="s2", tool_name="gh", tool_params={}),
        ]
        p = Plan(goal="build", steps=steps)
        assert len(p.steps) == 2


class TestAgentState:
    def test_initial_state(self):
        s = AgentState(goal="test goal")
        assert s.goal == "test goal"
        assert s.plan is None
        assert s.current_step_index == 0
        assert s.completed_steps == 0
        assert s.failed_steps == 0
        assert s.finished_at is None
        assert s.max_steps == 20

    def test_audit_trail(self):
        s = AgentState(goal="test")
        entry = AuditEntry(
            action="read file",
            tool_name="filesystem",
            risk_level=ActionRisk.LOW,
            decision=ApprovalDecision.AUTO_APPROVE,
        )
        s.audit_trail.append(entry)
        assert len(s.audit_trail) == 1
        assert s.audit_trail[0].tool_name == "filesystem"
