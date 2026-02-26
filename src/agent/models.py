"""Core data models for the agent framework."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(str, Enum):
    AUTO_APPROVE = "auto_approve"
    LOG_AND_APPROVE = "log_and_approve"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ToolResult(BaseModel):
    """Standardized result from an MCP tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    """A single step in the agent's execution plan."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str
    tool_name: str
    tool_params: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: ToolResult | None = None
    depends_on: list[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


class Plan(BaseModel):
    """An execution plan composed of ordered steps."""

    goal: str
    steps: list[Step] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEntry(BaseModel):
    """A single entry in the audit trail."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str
    tool_name: str | None = None
    tool_params: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None
    risk_level: ActionRisk = ActionRisk.LOW
    decision: ApprovalDecision = ApprovalDecision.AUTO_APPROVE
    rationale: str = ""


class AgentState(BaseModel):
    """Current state of the agent."""

    goal: str
    plan: Plan | None = None
    current_step_index: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    max_steps: int = 20
    timeout_seconds: int = 300
