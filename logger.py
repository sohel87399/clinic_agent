"""Structured JSON logger for the Closira AI workflow."""

import json
import os
from datetime import datetime, timezone
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ESCALATION_LOG_PATH = os.path.join(BASE_DIR, "escalation_log.json")
SESSION_LOG_PATH = os.path.join(BASE_DIR, "session_log.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: str, entry: dict) -> None:
    """Append a JSON entry to a log file (creates if not exists)."""
    entries: list = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            entries = []
    entries.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def log_escalation(session_id: str, reason: str, trigger_message: str, stage: str) -> None:
    """Log an escalation event to escalation_log.json."""
    entry = {
        "timestamp": _now(),
        "session_id": session_id,
        "stage": stage,
        "reason": reason,
        "trigger_message": trigger_message,
    }
    _append(ESCALATION_LOG_PATH, entry)


def log_session_event(session_id: str, event: str, data: Any = None) -> None:
    """Log a general session event to session_log.json."""
    entry = {
        "timestamp": _now(),
        "session_id": session_id,
        "event": event,
        "data": data,
    }
    _append(SESSION_LOG_PATH, entry)


def log_stage_transition(session_id: str, from_stage: str, to_stage: str) -> None:
    log_session_event(session_id, "stage_transition", {"from": from_stage, "to": to_stage})
