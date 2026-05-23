"""Convenience wrapper around stage_summary for direct use."""

from stages import stage_summary, SummaryResult


def generate_summary(
    conversation_history: list,
    qualification: dict,
    escalation: dict,
) -> SummaryResult:
    """Generate and return a structured session summary."""
    return stage_summary(conversation_history, qualification, escalation)
