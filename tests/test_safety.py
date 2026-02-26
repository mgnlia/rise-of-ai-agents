"""Tests for safety and observability modules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.models import ActionRisk, ApprovalDecision, AuditEntry, ToolResult
from safety.audit import AuditLogger
from safety.guardrails import Guardrails


class TestGuardrails:
    @pytest.fixture
    def guardrails(self):
        return Guardrails()

    def test_auto_approve_read(self, guardrails):
        decision = guardrails.check_action("filesystem", {"action": "read"})
        assert decision == ApprovalDecision.AUTO_APPROVE

    def test_log_and_approve_write(self, guardrails):
        decision = guardrails.check_action("filesystem", {"action": "write"})
        assert decision == ApprovalDecision.LOG_AND_APPROVE

    def test_require_approval_delete(self, guardrails):
        decision = guardrails.check_action("filesystem", {"action": "delete"})
        assert decision == ApprovalDecision.REQUIRE_APPROVAL

    def test_require_approval_code_executor(self, guardrails):
        decision = guardrails.check_action("code_executor", {"code": "print(1)"})
        assert decision == ApprovalDecision.REQUIRE_APPROVAL

    def test_auto_approve_web_search(self, guardrails):
        decision = guardrails.check_action("web_search", {"query": "test"})
        assert decision == ApprovalDecision.AUTO_APPROVE

    def test_unknown_tool_requires_approval(self, guardrails):
        decision = guardrails.check_action("unknown_tool", {"action": "do_stuff"})
        assert decision == ApprovalDecision.REQUIRE_APPROVAL

    def test_auto_approve_all_mode(self):
        g = Guardrails(auto_approve_all=True)
        decision = g.check_action("code_executor", {"code": "rm -rf /"})
        assert decision == ApprovalDecision.AUTO_APPROVE

    def test_is_sensitive(self, guardrails):
        assert guardrails.is_sensitive("code_executor", {"code": "x"}) is True
        assert guardrails.is_sensitive("web_search", {"query": "x"}) is False

    def test_add_policy(self, guardrails):
        guardrails.add_policy("custom_tool", "read", ApprovalDecision.AUTO_APPROVE)
        decision = guardrails.check_action("custom_tool", {"action": "read"})
        assert decision == ApprovalDecision.AUTO_APPROVE


class TestAuditLogger:
    @pytest.fixture
    def logger(self):
        return AuditLogger()

    def test_log_entry(self, logger):
        entry = AuditEntry(
            action="read file",
            tool_name="filesystem",
            tool_params={"action": "read", "path": "test.txt"},
            risk_level=ActionRisk.LOW,
            decision=ApprovalDecision.AUTO_APPROVE,
        )
        logger.log(entry)
        assert len(logger.get_entries()) == 1

    def test_filter_by_tool(self, logger):
        logger.log(AuditEntry(action="a1", tool_name="filesystem"))
        logger.log(AuditEntry(action="a2", tool_name="github"))
        logger.log(AuditEntry(action="a3", tool_name="filesystem"))

        fs_entries = logger.get_entries(tool_name="filesystem")
        assert len(fs_entries) == 2

    def test_summary(self, logger):
        logger.log(AuditEntry(
            action="read",
            tool_name="filesystem",
            risk_level=ActionRisk.LOW,
            decision=ApprovalDecision.AUTO_APPROVE,
            result=ToolResult(success=True),
        ))
        logger.log(AuditEntry(
            action="execute",
            tool_name="code_executor",
            risk_level=ActionRisk.HIGH,
            decision=ApprovalDecision.REQUIRE_APPROVAL,
            result=ToolResult(success=False, error="timeout"),
        ))

        summary = logger.summary()
        assert summary["total_entries"] == 2
        assert summary["failures"] == 1
        assert summary["by_tool"]["filesystem"] == 1
        assert summary["by_risk"]["high"] == 1

    def test_export_json(self, logger):
        logger.log(AuditEntry(action="test", tool_name="fs"))
        json_str = logger.export_json()
        assert "test" in json_str
        assert "fs" in json_str

    def test_file_persistence(self, tmp_path):
        log_file = str(tmp_path / "audit.jsonl")
        logger = AuditLogger(log_file=log_file)
        logger.log(AuditEntry(action="test", tool_name="fs"))

        # Verify file was written
        content = Path(log_file).read_text()
        assert "test" in content
        assert "fs" in content
