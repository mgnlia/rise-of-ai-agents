"""Action guardrails — approve, deny, or escalate tool actions based on policy."""

from __future__ import annotations

import logging
from typing import Any

from agent.models import ApprovalDecision

logger = logging.getLogger(__name__)

# Default policy: tool_name -> action -> decision
DEFAULT_POLICY: dict[str, dict[str, ApprovalDecision]] = {
    "github": {
        "read_file": ApprovalDecision.AUTO_APPROVE,
        "list_repos": ApprovalDecision.AUTO_APPROVE,
        "create_file": ApprovalDecision.LOG_AND_APPROVE,
        "create_repo": ApprovalDecision.REQUIRE_APPROVAL,
        "create_issue": ApprovalDecision.LOG_AND_APPROVE,
    },
    "filesystem": {
        "read": ApprovalDecision.AUTO_APPROVE,
        "list": ApprovalDecision.AUTO_APPROVE,
        "write": ApprovalDecision.LOG_AND_APPROVE,
        "mkdir": ApprovalDecision.LOG_AND_APPROVE,
        "delete": ApprovalDecision.REQUIRE_APPROVAL,
    },
    "web_search": {
        "*": ApprovalDecision.AUTO_APPROVE,
    },
    "code_executor": {
        "*": ApprovalDecision.REQUIRE_APPROVAL,
    },
}


class Guardrails:
    """Policy-based action approval system.

    Checks each tool action against a configurable policy and returns
    an approval decision: auto_approve, log_and_approve, require_approval, or deny.
    """

    def __init__(
        self,
        policy: dict[str, dict[str, ApprovalDecision]] | None = None,
        auto_approve_all: bool = False,
    ):
        self._policy = policy or DEFAULT_POLICY
        self._auto_approve_all = auto_approve_all
        self._approval_callbacks: list = []

    def check_action(self, tool_name: str, params: dict[str, Any]) -> ApprovalDecision:
        """Check whether an action should be approved, denied, or escalated."""
        if self._auto_approve_all:
            return ApprovalDecision.AUTO_APPROVE

        tool_policy = self._policy.get(tool_name, {})
        action = params.get("action", "*")

        # Check specific action first, then wildcard
        decision = tool_policy.get(action) or tool_policy.get("*")

        if decision is None:
            # Unknown tool/action — require approval by default
            logger.warning(
                "No policy for %s.%s — requiring approval", tool_name, action
            )
            return ApprovalDecision.REQUIRE_APPROVAL

        logger.info(
            "Guardrail check: %s.%s → %s", tool_name, action, decision.value
        )
        return decision

    def is_sensitive(self, tool_name: str, params: dict[str, Any]) -> bool:
        """Check if an action is considered sensitive (requires approval or is denied)."""
        decision = self.check_action(tool_name, params)
        return decision in (ApprovalDecision.REQUIRE_APPROVAL, ApprovalDecision.DENY)

    def add_policy(self, tool_name: str, action: str, decision: ApprovalDecision) -> None:
        """Add or update a policy rule."""
        if tool_name not in self._policy:
            self._policy[tool_name] = {}
        self._policy[tool_name][action] = decision
