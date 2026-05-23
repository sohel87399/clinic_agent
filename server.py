"""
Flask API server for the Closira AI Agent web frontend.
Manages per-session workflow instances and exposes REST endpoints.
"""

import os
import sys
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Force load .env before any other imports that use the key
load_dotenv(override=True)

# Ensure GROQ key is present — warn but don't exit (Vercel sets it via dashboard)
if not os.environ.get("GROQ_API_KEY"):
    print("⚠️  GROQ_API_KEY not found — set it in Vercel environment variables")

from workflow import ClosiraWorkflow

app = Flask(__name__)
CORS(app)

SOP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sop", "bloom_aesthetics.json")

# In-memory session store: session_id -> ClosiraWorkflow instance
_sessions: dict = {}


def _get_or_create_session(session_id: str) -> ClosiraWorkflow:
    if session_id not in _sessions:
        _sessions[session_id] = ClosiraWorkflow(SOP_PATH)
    return _sessions[session_id]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session/new", methods=["POST"])
def new_session():
    """Create a new conversation session."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = ClosiraWorkflow(SOP_PATH)
    return jsonify({
        "session_id": session_id,
        "message": "Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, your virtual assistant. How can I help you today?",
        "stage": "FAQ_ANSWERING",
        "escalated": False,
        "session_ended": False,
    })


@app.route("/api/message", methods=["POST"])
def send_message():
    """Send a message and get a response."""
    data = request.get_json()
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()

    if not session_id or not user_message:
        return jsonify({"error": "session_id and message are required"}), 400

    try:
        workflow = _get_or_create_session(session_id)
        response = workflow.process_message(user_message)

        return jsonify({
            "message": response.message,
            "stage": response.stage,
            "escalated": response.escalated,
            "session_ended": response.session_ended,
            "qualification_complete": response.qualification_complete,
            "summary": response.summary,
            "metadata": response.metadata,
        })
    except Exception as e:
        print(f"[ERROR] /api/message: {e}")
        import traceback; traceback.print_exc()
        return jsonify({
            "message": f"Sorry, I encountered an error: {str(e)}",
            "stage": "FAQ_ANSWERING",
            "escalated": False,
            "session_ended": False,
            "qualification_complete": False,
            "summary": None,
            "metadata": {},
        }), 200


@app.route("/api/session/<session_id>/end", methods=["POST"])
def end_session(session_id: str):
    """End a session and get the summary."""
    if session_id not in _sessions:
        return jsonify({"error": "Session not found"}), 404

    workflow = _sessions[session_id]
    response = workflow.end_session()
    del _sessions[session_id]

    return jsonify({
        "message": response.message,
        "stage": response.stage,
        "session_ended": True,
        "summary": response.summary,
    })


@app.route("/api/session/<session_id>/status", methods=["GET"])
def session_status(session_id: str):
    """Get current session stage."""
    if session_id not in _sessions:
        return jsonify({"error": "Session not found"}), 404
    workflow = _sessions[session_id]
    return jsonify({
        "session_id": session_id,
        "stage": workflow.current_stage.value,
        "escalated": workflow.current_stage.value == "ESCALATED",
    })


if __name__ == "__main__":
    print("\n🌸  Bloom Aesthetics — Closira AI Agent")
    print("    Running at: http://localhost:5000\n")
    app.run(debug=False, port=5000, use_reloader=False)
