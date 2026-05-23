# Closira AI Agent

A production-quality, 4-stage AI customer support workflow built with Python and the Anthropic Claude API. Designed as a hiring assignment for Closira — demonstrating clean architecture, prompt engineering, and AI workflow design.

---

## Setup

### 1. Prerequisites
- Python 3.10+
- An Anthropic API key ([get one here](https://console.anthropic.com/))

### 2. Install dependencies

```bash
cd closira-ai-agent
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 4. Run

```bash
python main.py
```

---

## Folder Structure

```
closira-ai-agent/
├── main.py               # CLI entry point
├── workflow.py           # Stage orchestration (ClosiraWorkflow class)
├── stages.py             # 4 stage functions + Claude API calls
├── escalation.py         # Pattern-based escalation detection
├── summary.py            # Summary convenience wrapper
├── logger.py             # Structured JSON logging
├── prompt_design.md      # Prompt engineering decisions
├── requirements.txt
├── .env.example
├── sop/
│   └── bloom_aesthetics.json   # Clinic SOP data
├── prompts/
│   └── system_prompt.txt       # Full system prompt
└── test_transcripts/
    ├── 01_in_sop_question.md
    ├── 02_out_of_scope_question.md
    ├── 03_escalation_trigger.md
    ├── 04_lead_qualification.md
    └── 05_conversation_summary.md
```

---

## Architecture

### Stage Flow

```
START
  │
  ▼
FAQ_ANSWERING ──────────────────────────────────────────► ESCALATED (terminal)
  │  (after first successful answer)                        ▲
  ▼                                                         │
LEAD_QUALIFICATION ─────────────────────────────────────────┤
  │  (after all 3 questions answered)                       │
  ▼                                                         │
SUMMARY ────────────────────────────────────────────────────┘
  │
  ▼
ENDED
```

### Two-Layer Escalation

```
User message
     │
     ▼
Layer 1: Pattern matching (escalation.py)
  - Explicit: "manager", "complaint", "speak to human"
  - Medical: "allergies", "medication", "side effects"
  - Pricing: "discount", "cheaper", "negotiate"
  - Sentiment: "ridiculous", "unacceptable", ALL CAPS
     │
     │ (if no pattern match)
     ▼
Layer 2: Claude-level detection (stages.py)
  - ESCALATE: flag in response
  - OUT_OF_SCOPE flag
  - Confidence < 0.6
  - Repeated question (>2 times)
```

---

## The 4 Stages

### Stage 1: FAQ Answering
- Injects SOP data as structured context
- Claude answers strictly from SOP
- Returns confidence score (0.0–1.0)
- Escalates if confidence < 0.6 or question is out of scope

### Stage 2: Lead Qualification
- Asks 3 questions conversationally, one at a time
- Tracks answered questions from conversation history
- Produces structured qualification: `{interested_service, prior_experience, booking_intent, lead_score}`
- Lead score: `hot` (specific + soon) | `warm` (exploring) | `cold` (vague)

### Stage 3: Escalation Detection
- Two-layer: pattern-based (fast) + Claude-level (nuanced)
- 6 trigger types: explicit, sentiment, medical, out_of_scope, low_confidence, repeated, pricing
- Logs to `escalation_log.json` with timestamp
- Terminal state — no further AI responses

### Stage 4: Conversation Summary
- Generates structured JSON summary via Claude
- Captures: customer intent, details collected, SOP gaps, escalation info
- Includes recommended next action for the human team

---

## Logging

Two log files are created automatically:

**`escalation_log.json`** — every escalation event:
```json
[{
  "timestamp": "2025-05-20T09:14:00Z",
  "session_id": "a3f2b1c4",
  "stage": "FAQ_ANSWERING",
  "reason": "Customer asked a medical question",
  "trigger_message": "I'm on blood thinners, is Botox safe?"
}]
```

**`session_log.json`** — stage transitions and session events:
```json
[{
  "timestamp": "2025-05-20T09:10:00Z",
  "session_id": "a3f2b1c4",
  "event": "stage_transition",
  "data": {"from": "FAQ_ANSWERING", "to": "LEAD_QUALIFICATION"}
}]
```

---

## Example Session

```
You: How much does Botox cost?

🤖 Aria [LEAD_QUALIFICATION]
──────────────────────────────────────────────────────
Our Botox treatments start from £200, and that includes your initial
consultation. Results typically last 3–4 months.

While I have you — mind if I ask a couple of quick questions?

Which service are you most interested in?
   Confidence: [████████░░] 90%

You: Botox for sure

🤖 Aria [LEAD_QUALIFICATION]
──────────────────────────────────────────────────────
Great choice! Have you had aesthetic treatments before?

You: No, first time

🤖 Aria [LEAD_QUALIFICATION]
──────────────────────────────────────────────────────
No worries at all — our free consultation is perfect for first-timers.
Are you looking to book soon, or just exploring options?

You: I want to book next week

🤖 Aria [SUMMARY]
──────────────────────────────────────────────────────
That's wonderful! 🔥 Lead score: **HOT**

Type 'done' to get your session summary.

You: done

✅ [ENDED]
──────────────────────────────────────────────────────
{
  "customer_intent": "Book a Botox appointment",
  "details_collected": {
    "interested_service": "Botox",
    "prior_experience": "No previous treatments",
    "booking_intent": "Looking to book next week"
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "Book a free Botox consultation — hot lead"
}
```

---

## Design Decisions

See [`prompt_design.md`](prompt_design.md) for full rationale on:
- Single system prompt vs per-stage prompts
- Structured output markers (CONFIDENCE, ESCALATE, QUALIFICATION tags)
- Two-layer escalation architecture
- SOP injection format
- Confidence threshold (0.6)
- Model selection (claude-sonnet-4-5)

---

## Known Limitations

- **In-memory only** — conversation history resets on restart; needs Redis/DB for production
- **Self-reported confidence** — Claude's confidence scores are not perfectly calibrated
- **English only** — no multi-language support
- **No streaming** — responses are returned in full; streaming would improve UX
- **Single SOP** — designed for one clinic; multi-tenant would need SOP routing

## What I'd Add With More Time

- RAG with vector search for larger SOP knowledge bases
- Streaming responses via `anthropic.stream()`
- Unit tests for each stage function
- FastAPI wrapper to expose as HTTP endpoints
- Webhook integration to post escalations to Slack/CRM
- Conversation persistence with SQLite
