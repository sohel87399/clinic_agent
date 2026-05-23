"""
Closira AI Agent — CLI entry point.

Usage:
    python main.py

Requires:
    ANTHROPIC_API_KEY set in .env file
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Validate API key before starting
if not os.environ.get("GROQ_API_KEY"):
    print("❌  GROQ_API_KEY not found.")
    print("    Copy .env.example to .env and add your Groq API key.")
    print("    Get a free key at: https://console.groq.com")
    sys.exit(1)

from workflow import ClosiraWorkflow  # noqa: E402 — import after env check

SOP_PATH = os.path.join(os.path.dirname(__file__), "sop", "bloom_aesthetics.json")

BANNER = """
╔══════════════════════════════════════════════════════╗
║        Bloom Aesthetics Clinic — AI Assistant        ║
║                  Powered by Closira                  ║
╚══════════════════════════════════════════════════════╝
  Type your message and press Enter.
  Type 'exit', 'bye', or 'done' to end the session.
  Type 'help' to see available commands.
──────────────────────────────────────────────────────
"""

HELP_TEXT = """
Commands:
  exit / bye / done / quit  — End session and get summary
  help                      — Show this help message
  stage                     — Show current workflow stage
"""


def print_response(response) -> None:
    """Pretty-print a WorkflowResponse."""
    stage_label = f"[{response.stage}]"

    if response.escalated:
        print(f"\n🚨 {stage_label}")
    elif response.session_ended:
        print(f"\n✅ {stage_label}")
    else:
        print(f"\n🤖 Aria {stage_label}")

    print("─" * 54)
    print(response.message)
    print("─" * 54)

    if response.metadata.get("confidence") is not None:
        conf = response.metadata["confidence"]
        bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
        print(f"   Confidence: [{bar}] {conf:.0%}")


def main() -> None:
    print(BANNER)

    workflow = ClosiraWorkflow(SOP_PATH)
    print(f"   Session ID: {workflow.session_id}\n")

    # Opening greeting
    print("🤖 Aria [FAQ_ANSWERING]")
    print("─" * 54)
    print("Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, your virtual assistant.")
    print("How can I help you today?")
    print("─" * 54)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession interrupted.")
            break

        if not user_input:
            continue

        if user_input.lower() == "help":
            print(HELP_TEXT)
            continue

        if user_input.lower() == "stage":
            print(f"   Current stage: {workflow.current_stage.value}")
            continue

        response = workflow.process_message(user_input)
        print_response(response)

        if response.session_ended or response.escalated:
            break

    print("\n👋  Session ended. Thank you for using Closira.\n")


if __name__ == "__main__":
    main()
