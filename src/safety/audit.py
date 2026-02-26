"""Audit trail logger — records every agent action for post-hoc review."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.models import AuditEntry

logger = logging.getLogger(__name__)


class AuditLogger:
    """Persistent audit trail for all agent actions.

    Records every tool call with timestamp, parameters, result, risk level,
    and approval decision. Supports both in-memory and file-based persistence.
    """

    def __init__(self, log_file: str | None = None):
        self._entries: list[AuditEntry] = []
        self._log_file = Path(log_file) if log_file else None

        if self._log_file:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AuditEntry) -> None:
        """Record an audit entry."""
        self._entries.append(entry)
        logger.info(
            "AUDIT: %s | tool=%s | risk=%s | decision=%s",
            entry.action,
            entry.tool_name,
            entry.risk_level.value,
            entry.decision.value,
        )

        if self._log_file:
            self._append_to_file(entry)

    def get_entries(
        self,
        tool_name: str | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        entries = self._entries

        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]

        if since:
            entries = [e for e in entries if e.timestamp >= since]

        return entries

    def summary(self) -> dict[str, Any]:
        """Generate a summary of the audit trail."""
        total = len(self._entries)
        by_tool: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        failures = 0

        for entry in self._entries:
            tool = entry.tool_name or "unknown"
            by_tool[tool] = by_tool.get(tool, 0) + 1
            by_risk[entry.risk_level.value] = by_risk.get(entry.risk_level.value, 0) + 1
            by_decision[entry.decision.value] = by_decision.get(entry.decision.value, 0) + 1

            if entry.result and not entry.result.success:
                failures += 1

        return {
            "total_entries": total,
            "failures": failures,
            "by_tool": by_tool,
            "by_risk": by_risk,
            "by_decision": by_decision,
        }

    def _append_to_file(self, entry: AuditEntry) -> None:
        """Append a single entry to the log file as JSON Lines."""
        try:
            with open(self._log_file, "a") as f:  # type: ignore[arg-type]
                data = {
                    "timestamp": entry.timestamp.isoformat(),
                    "action": entry.action,
                    "tool_name": entry.tool_name,
                    "risk_level": entry.risk_level.value,
                    "decision": entry.decision.value,
                    "rationale": entry.rationale,
                    "success": entry.result.success if entry.result else None,
                    "error": entry.result.error if entry.result else None,
                }
                f.write(json.dumps(data) + "\n")
        except OSError as e:
            logger.error("Failed to write audit log: %s", e)

    def export_json(self) -> str:
        """Export the full audit trail as JSON."""
        entries = []
        for e in self._entries:
            entries.append({
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "tool_name": e.tool_name,
                "tool_params": e.tool_params,
                "risk_level": e.risk_level.value,
                "decision": e.decision.value,
                "rationale": e.rationale,
                "success": e.result.success if e.result else None,
            })
        return json.dumps(entries, indent=2)
