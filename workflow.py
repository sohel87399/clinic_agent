"""
Core 4-stage workflow orchestration for the Closira AI agent.

Stage flow:
  START → FAQ_ANSWERING → LEAD_QUALIFICATION → SUMMARY → END
  Any stage → ESCALATED (terminal)
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from escalation import detect_escalation
from logger import log_escalation, log_session_event, log_stage_transition
from stages import (
    StageResult,
    QualificationResult,
    SummaryResult,
    stage_faq,
    stage_lead_qualification,
    stage_escalation_detection,
    stage_summary,
)


# ── Stage enum ────────────────────────────────────────────────────────────────

class Stage(str, Enum):
    FAQ_ANSWERING      = "FAQ_ANSWERING"
    LEAD_QUALIFICATION = "LEAD_QUALIFICATION"
    SUMMARY            = "SUMMARY"
    ESCALATED          = "ESCALATED"
    ENDED              = "ENDED"


# ── Response dataclass ────────────────────────────────────────────────────────

@dataclass
class WorkflowResponse:
    message: str
    stage: str
    escalated: bool = False
    qualification_complete: bool = False
    session_ended: bool = False
    summary: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


# ── Workflow class ────────────────────────────────────────────────────────────

class ClosiraWorkflow:

    def __init__(self, sop_path: str):
        with open(sop_path, "r", encoding="utf-8") as f:
            self.sop: dict = json.load(f)

        self.session_id: str = str(uuid.uuid4())[:8]
        self.current_stage: Stage = Stage.FAQ_ANSWERING
        self.conversation_history: list = []
        self.qualification: dict = {}
        self.escalation_info: dict = {}
        self.sop_gaps: list = []
        self.unanswered_count: int = 0
        self.question_counts: dict = {}   # track repeated questions

        log_session_event(self.session_id, "session_start", {"sop": self.sop["business"]})

    # ── Public entry point ────────────────────────────────────────────────────

    def process_message(self, user_message: str) -> WorkflowResponse:
        """Route a user message through the appropriate workflow stage."""

        # Terminal states — no more processing
        if self.current_stage in (Stage.ESCALATED, Stage.ENDED):
            return WorkflowResponse(
                message="This session has ended. Please start a new conversation.",
                stage=self.current_stage.value,
                escalated=self.current_stage == Stage.ESCALATED,
                session_ended=True,
            )

        # Exit keywords
        if user_message.strip().lower() in ("exit", "bye", "done", "quit", "goodbye"):
            return self.end_session()

        # ── Step 1: Pre-screen for escalation triggers (pattern-based, fast) ──
        esc_check = detect_escalation(user_message)
        if esc_check.escalated:
            return self._handle_escalation(
                user_message,
                esc_check.reason,
                esc_check.trigger_type,
            )

        # ── Step 2: Track repeated questions ──────────────────────────────────
        msg_key = user_message.strip().lower()[:60]
        self.question_counts[msg_key] = self.question_counts.get(msg_key, 0) + 1
        if self.question_counts[msg_key] > 2:
            return self._handle_escalation(
                user_message,
                "Same question asked more than twice without resolution",
                "repeated",
            )

        # ── Step 3: Route to current stage ────────────────────────────────────
        if self.current_stage == Stage.FAQ_ANSWERING:
            return self._run_faq(user_message)

        if self.current_stage == Stage.LEAD_QUALIFICATION:
            return self._run_qualification(user_message)

        if self.current_stage == Stage.SUMMARY:
            return self.end_session()

        return WorkflowResponse(message="Unknown state.", stage=self.current_stage.value)

    def end_session(self) -> WorkflowResponse:
        """Run stage_summary and mark session as ended."""
        result: SummaryResult = stage_summary(
            self.conversation_history,
            self.qualification,
            self.escalation_info,
        )
        self.current_stage = Stage.ENDED
        log_session_event(self.session_id, "session_end", result.summary)

        return WorkflowResponse(
            message=f"Thanks for chatting with Bloom Aesthetics! Here's a summary of our conversation:\n\n{result.formatted}",
            stage=Stage.ENDED.value,
            session_ended=True,
            summary=result.summary,
        )

    # ── Private stage runners ─────────────────────────────────────────────────

    def _run_faq(self, user_message: str) -> WorkflowResponse:
        """Run Stage 1: FAQ answering."""
        result: StageResult = stage_faq(
            user_message, self.sop, self.conversation_history
        )

        # Append to history
        self._append_history(user_message, result.response)

        # Escalate on low confidence or out-of-scope
        if result.should_escalate:
            if result.escalation_reason == "out_of_scope":
                self.sop_gaps.append(user_message)
                self.unanswered_count += 1
                # Give one clarification attempt before escalating
                if self.unanswered_count >= 2:
                    return self._handle_escalation(
                        user_message,
                        "Question could not be answered from SOP after multiple attempts",
                        "out_of_scope",
                    )
                # First attempt — return the polite out-of-scope message
                return WorkflowResponse(
                    message=result.response,
                    stage=self.current_stage.value,
                    metadata={"confidence": result.confidence},
                )
            else:
                return self._handle_escalation(
                    user_message,
                    result.escalation_reason or "Low confidence answer",
                    result.escalation_reason or "low_confidence",
                )

        # Reset unanswered counter on successful answer
        self.unanswered_count = 0

        # After a successful FAQ answer, transition to lead qualification
        next_stage_msg = ""
        if self.current_stage == Stage.FAQ_ANSWERING:
            log_stage_transition(self.session_id, Stage.FAQ_ANSWERING.value, Stage.LEAD_QUALIFICATION.value)
            self.current_stage = Stage.LEAD_QUALIFICATION
            next_stage_msg = "\n\nWhile I have you — mind if I ask a couple of quick questions to make sure we can help you in the best way possible?"

        return WorkflowResponse(
            message=result.response + next_stage_msg,
            stage=self.current_stage.value,
            metadata={"confidence": result.confidence},
        )

    def _run_qualification(self, user_message: str) -> WorkflowResponse:
        """Run Stage 2: Lead qualification."""
        self._append_history(user_message, "")  # append user turn first

        result: QualificationResult = stage_lead_qualification(
            self.conversation_history, self.sop
        )

        # Update the last assistant turn with the actual response
        if self.conversation_history and self.conversation_history[-1]["role"] == "user":
            self.conversation_history.append({"role": "assistant", "content": result.response})
        else:
            self._update_last_assistant(result.response)

        if result.complete:
            self.qualification = result.qualification
            log_session_event(self.session_id, "qualification_complete", result.qualification)
            log_stage_transition(self.session_id, Stage.LEAD_QUALIFICATION.value, Stage.SUMMARY.value)
            self.current_stage = Stage.SUMMARY

            score = result.qualification.get("lead_score", "warm")
            score_emoji = {"hot": "🔥", "warm": "😊", "cold": "❄️"}.get(score, "")
            footer = f"\n\n{score_emoji} Lead score: **{score.upper()}**\n\nType 'done' to get your session summary, or ask another question."

            return WorkflowResponse(
                message=result.response + footer,
                stage=self.current_stage.value,
                qualification_complete=True,
                metadata={"qualification": result.qualification},
            )

        return WorkflowResponse(
            message=result.response,
            stage=self.current_stage.value,
        )

    def _handle_escalation(
        self, user_message: str, reason: str, trigger_type: str
    ) -> WorkflowResponse:
        """Escalate the session — terminal state."""
        esc_result = stage_escalation_detection(
            user_message,
            self.conversation_history,
            reason=reason,
            trigger_type=trigger_type,
        )

        self.escalation_info = {
            "reason": reason,
            "trigger_type": trigger_type,
            "trigger_message": user_message,
        }

        log_escalation(self.session_id, reason, user_message, self.current_stage.value)
        log_stage_transition(self.session_id, self.current_stage.value, Stage.ESCALATED.value)
        self.current_stage = Stage.ESCALATED

        return WorkflowResponse(
            message=esc_result.handoff_message,
            stage=Stage.ESCALATED.value,
            escalated=True,
            metadata={"reason": reason, "trigger_type": trigger_type},
        )

    # ── History helpers ───────────────────────────────────────────────────────

    def _append_history(self, user_message: str, assistant_response: str) -> None:
        self.conversation_history.append({"role": "user", "content": user_message})
        if assistant_response:
            self.conversation_history.append({"role": "assistant", "content": assistant_response})

    def _update_last_assistant(self, response: str) -> None:
        for i in range(len(self.conversation_history) - 1, -1, -1):
            if self.conversation_history[i]["role"] == "assistant":
                self.conversation_history[i]["content"] = response
                return
        self.conversation_history.append({"role": "assistant", "content": response})
