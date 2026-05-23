"""
Flask API server for the Closira AI Agent web frontend.
Stateless design — conversation state is held client-side and sent with each request.
This works correctly on Vercel serverless where in-memory state is lost between requests.
"""

import os
import sys
import uuid
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(override=True)

if not os.environ.get("GROQ_API_KEY"):
    print("⚠️  GROQ_API_KEY not found — set it in Vercel environment variables")

from stages import (
    stage_faq,
    stage_lead_qualification,
    stage_escalation_detection,
    stage_summary,
)
from escalation import detect_escalation

app = Flask(__name__)
CORS(app)

# Resolve SOP path — tries multiple locations for Vercel compatibility
_here = os.path.dirname(os.path.abspath(__file__))
_sop_candidates = [
    os.path.join(_here, "sop", "bloom_aesthetics.json"),
    os.path.join(_here, "..", "sop", "bloom_aesthetics.json"),
    os.path.join(os.getcwd(), "sop", "bloom_aesthetics.json"),
]
SOP_PATH = next((p for p in _sop_candidates if os.path.exists(p)), _sop_candidates[0])

# Load SOP once at startup
with open(SOP_PATH, "r", encoding="utf-8") as f:
    SOP = json.load(f)


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
        "sop_found": os.path.exists(SOP_PATH),
        "sop_path": SOP_PATH,
    })


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session/new", methods=["POST"])
def new_session():
    """Start a new session — returns initial state to client."""
    return jsonify({
        "session_id": str(uuid.uuid4()),
        "message": "Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, your virtual assistant. How can I help you today?",
        "stage": "FAQ_ANSWERING",
        "escalated": False,
        "session_ended": False,
        # Client stores and sends back this state on every message
        "state": {
            "stage": "FAQ_ANSWERING",
            "history": [],
            "qualification": {},
            "escalation_info": {},
            "unanswered_count": 0,
            "question_counts": {},
        }
    })


@app.route("/api/message", methods=["POST"])
def send_message():
    """
    Stateless message handler.
    Client sends: { session_id, message, state }
    Server returns: { message, stage, ..., state }  ← updated state sent back
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user_message = data.get("message", "").strip()
    state = data.get("state") or {
        "stage": "FAQ_ANSWERING",
        "history": [],
        "qualification": {},
        "escalation_info": {},
        "unanswered_count": 0,
        "question_counts": {},
    }

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    try:
        result = _process(user_message, state)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "message": f"Sorry, something went wrong: {str(e)}",
            "stage": state.get("stage", "FAQ_ANSWERING"),
            "escalated": False,
            "session_ended": False,
            "qualification_complete": False,
            "summary": None,
            "metadata": {},
            "state": state,
        }), 200


@app.route("/api/session/<session_id>/end", methods=["POST"])
def end_session(session_id: str):
    """End session — client sends state, server returns summary."""
    data = request.get_json() or {}
    state = data.get("state") or {"history": [], "qualification": {}, "escalation_info": {}}

    result = stage_summary(
        state.get("history", []),
        state.get("qualification", {}),
        state.get("escalation_info", {}),
    )

    return jsonify({
        "message": f"Thanks for chatting with Bloom Aesthetics! Here's a summary:\n\n{result.formatted}",
        "stage": "ENDED",
        "session_ended": True,
        "summary": result.summary,
    })


# ── Core stateless processor ──────────────────────────────────────────────────

def _process(user_message: str, state: dict) -> dict:
    """Process one message given current state, return response + updated state."""

    stage = state.get("stage", "FAQ_ANSWERING")
    history = state.get("history", [])
    qualification = state.get("qualification", {})
    escalation_info = state.get("escalation_info", {})
    unanswered_count = state.get("unanswered_count", 0)
    question_counts = state.get("question_counts", {})

    # Terminal states
    if stage in ("ESCALATED", "ENDED"):
        return _resp("This session has ended. Please start a new conversation.",
                     stage, state, session_ended=True, escalated=(stage == "ESCALATED"))

    # Exit keywords → summary
    if user_message.strip().lower() in ("exit", "bye", "done", "quit", "goodbye"):
        result = stage_summary(history, qualification, escalation_info)
        state["stage"] = "ENDED"
        return _resp(
            f"Thanks for chatting with Bloom Aesthetics! Here's a summary:\n\n{result.formatted}",
            "ENDED", state, session_ended=True, summary=result.summary
        )

    # Layer 1: pattern-based escalation
    esc_check = detect_escalation(user_message)
    if esc_check.escalated:
        return _escalate(user_message, esc_check.reason, esc_check.trigger_type, state)

    # Repeated question guard
    msg_key = user_message.strip().lower()[:60]
    question_counts[msg_key] = question_counts.get(msg_key, 0) + 1
    state["question_counts"] = question_counts
    if question_counts[msg_key] > 2:
        return _escalate(user_message, "Same question asked more than twice", "repeated", state)

    # Route by stage
    if stage == "FAQ_ANSWERING":
        return _run_faq(user_message, state, history, unanswered_count)

    if stage == "LEAD_QUALIFICATION":
        return _run_qualification(user_message, state, history, qualification, escalation_info)

    if stage == "SUMMARY":
        result = stage_summary(history, qualification, escalation_info)
        state["stage"] = "ENDED"
        return _resp(
            f"Thanks for chatting! Here's your summary:\n\n{result.formatted}",
            "ENDED", state, session_ended=True, summary=result.summary
        )

    return _resp("Unknown state.", stage, state)


def _run_faq(user_message, state, history, unanswered_count):
    result = stage_faq(user_message, SOP, history)

    if result.should_escalate:
        if result.escalation_reason == "out_of_scope":
            unanswered_count += 1
            state["unanswered_count"] = unanswered_count
            if unanswered_count >= 2:
                return _escalate(user_message, "Could not answer from SOP after multiple attempts", "out_of_scope", state)
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": result.response})
            state["history"] = history
            return _resp(result.response, "FAQ_ANSWERING", state, metadata={"confidence": result.confidence})
        else:
            return _escalate(user_message, result.escalation_reason or "Low confidence", result.escalation_reason or "low_confidence", state)

    state["unanswered_count"] = 0
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": result.response})
    state["history"] = history
    state["stage"] = "LEAD_QUALIFICATION"

    next_msg = result.response + "\n\nWhile I have you — mind if I ask a couple of quick questions to make sure we can help you in the best way possible?"
    return _resp(next_msg, "LEAD_QUALIFICATION", state, metadata={"confidence": result.confidence})


def _run_qualification(user_message, state, history, qualification, escalation_info):
    history.append({"role": "user", "content": user_message})
    state["history"] = history

    result = stage_lead_qualification(history, SOP)

    history.append({"role": "assistant", "content": result.response})
    state["history"] = history

    if result.complete:
        state["qualification"] = result.qualification
        state["stage"] = "SUMMARY"
        score = result.qualification.get("lead_score", "warm")
        score_emoji = {"hot": "🔥", "warm": "😊", "cold": "❄️"}.get(score, "")
        footer = f"\n\n{score_emoji} Lead score: **{score.upper()}**\n\nType 'done' to get your session summary, or ask another question."
        return _resp(result.response + footer, "SUMMARY", state,
                     qualification_complete=True,
                     metadata={"qualification": result.qualification})

    return _resp(result.response, "LEAD_QUALIFICATION", state)


def _escalate(user_message, reason, trigger_type, state):
    esc_result = stage_escalation_detection(
        user_message, state.get("history", []),
        reason=reason, trigger_type=trigger_type
    )
    state["stage"] = "ESCALATED"
    state["escalation_info"] = {"reason": reason, "trigger_type": trigger_type}
    return _resp(esc_result.handoff_message, "ESCALATED", state,
                 escalated=True, metadata={"reason": reason, "trigger_type": trigger_type})


def _resp(message, stage, state, escalated=False, session_ended=False,
          qualification_complete=False, summary=None, metadata=None):
    return {
        "message": message,
        "stage": stage,
        "escalated": escalated,
        "session_ended": session_ended,
        "qualification_complete": qualification_complete,
        "summary": summary,
        "metadata": metadata or {},
        "state": state,
    }


if __name__ == "__main__":
    print("\n🌸  Bloom Aesthetics — Closira AI Agent")
    print("    Running at: http://localhost:5000\n")
    app.run(debug=False, port=5000, use_reloader=False)
