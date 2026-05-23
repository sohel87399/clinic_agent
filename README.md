# Closira AI Agent — Bloom Aesthetics Clinic

> **Live Demo → (clinic-agent-git-main-sohels-projects-ef12fbd0.vercel.app)**
> *(No setup needed — just open and chat)*

A production-quality, 4-stage AI customer support agent built for **Bloom Aesthetics Clinic**. Built with Python, Flask, and the Groq API (Llama 3.3 70B). Designed as a hiring assignment for Closira — demonstrating clean architecture, prompt engineering, and multi-stage AI workflow design.

---

## What It Does

The agent, **Aria**, handles the full customer support lifecycle in 4 automated stages:

| Stage | What happens |
|-------|-------------|
| **1. FAQ Answering** | Answers questions strictly from the clinic's SOP — pricing, services, hours, booking |
| **2. Lead Qualification** | Asks 3 conversational questions to score the lead (hot / warm / cold) |
| **3. Escalation** | Detects frustration, medical questions, or out-of-scope queries and hands off to a human |
| **4. Summary** | Generates a structured JSON summary of the session for the clinic's CRM |

---

## Try It (For Recruiters)

**Option 1 — Live web app (easiest):**
1. Open → **[https://clinic-agent-6pj3d7nqd-sohels-projects-ef12fbd0.vercel.app](https://clinic-agent-6pj3d7nqd-sohels-projects-ef12fbd0.vercel.app)**
2. Start chatting with Aria
3. Try these sample messages to see different behaviours:

| What to type | What it demonstrates |
|---|---|
| `How much does Botox cost?` | FAQ answering from SOP |
| `I want to speak to a manager` | Escalation trigger |
| `Can I take it if I'm on blood thinners?` | Medical question → escalation |
| `What's the weather like?` | Out-of-scope handling |
| After a few messages, type `done` | Session summary generation |

**Option 2 — Run locally:**
```bash
git clone https://github.com/sohel87399/clinic_agent.git
cd clinic_agent
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
python server.py       # open http://localhost:5000
```

---

## Tech Stack

- **LLM:** Groq API — `llama-3.3-70b-versatile` (free tier, 14,400 req/day)
- **Backend:** Python + Flask
- **Frontend:** Vanilla JS + CSS (no framework)
- **Deployment:** Vercel (serverless)
- **Prompt design:** Single structured system prompt with output markers

---

## Setup

### 1. Prerequisites
- Python 3.10+
- A Groq API key — free at [console.groq.com](https://console.groq.com)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Run

**Web UI (recommended):**
```bash
python server.py
# Open http://localhost:5000
```

**CLI mode:**
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

- **Stateless on Vercel** — in-memory sessions don't persist across serverless instances; needs Redis for production scale
- **Self-reported confidence** — the LLM's confidence scores are not perfectly calibrated
- **English only** — no multi-language support
- **No streaming** — responses returned in full; streaming would improve perceived speed
- **Single SOP** — designed for one clinic; multi-tenant would need SOP routing

## What I'd Add With More Time

- RAG with vector search for larger SOP knowledge bases
- Streaming responses via `anthropic.stream()`
- Unit tests for each stage function
- FastAPI wrapper to expose as HTTP endpoints
- Webhook integration to post escalations to Slack/CRM
- Conversation persistence with SQLite
