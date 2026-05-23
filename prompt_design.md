# Prompt Design Decisions

## Overview

This document explains the key prompt engineering decisions made for the Closira AI workflow.

---

## 1. Single System Prompt, Stage-Aware Context

Rather than maintaining separate system prompts per stage, a single master system prompt (`SYSTEM_PROMPT` in `stages.py`) is used across all stages. Stage-specific behaviour is injected as additional context blocks appended to the system prompt at call time.

**Why:** Keeps the AI's persona (Aria) consistent across all stages. Avoids jarring tone shifts when transitioning from FAQ to qualification.

**Trade-off:** Slightly larger token usage per call. Acceptable given the short conversation length.

---

## 2. Structured Output Markers

Claude is instructed to use explicit output markers:
- `CONFIDENCE: 0.85` — machine-parseable confidence score
- `OUT_OF_SCOPE` — first-line flag for unanswerable questions
- `ESCALATE: [reason]` — first-line flag for escalation
- `<QUALIFICATION>...</QUALIFICATION>` — JSON block for qualification data

**Why:** Avoids brittle regex parsing of natural language. These markers are unambiguous and easy to extract reliably.

**Alternative considered:** Asking Claude to return JSON for every response. Rejected because it makes conversational responses feel robotic and harder to display naturally.

---

## 3. Two-Layer Escalation Detection

Escalation is detected at two layers:

**Layer 1 — Pattern matching (`escalation.py`):**
Fast, zero-latency regex checks run before any Claude API call. Catches explicit triggers (manager, complaint, medical keywords, pricing negotiation, ALL CAPS) without spending tokens.

**Layer 2 — Claude-level detection (`stages.py`):**
Claude can flag `ESCALATE:` in its response for nuanced cases (e.g. implied frustration, subtle medical questions) that regex would miss.

**Why:** Pattern matching is deterministic and instant. Claude catches edge cases. Together they provide high recall with low false-negative rate.

---

## 4. SOP Injection as Structured Text

The SOP JSON is rendered into a human-readable text block and injected into the system prompt context, not passed as raw JSON.

**Why:** Claude performs better with natural language context than raw JSON. The structured text format mirrors how a human agent would read a reference document.

**Example:**
```
SERVICES:
  - Botox: £200. Anti-wrinkle treatment. Results last 3-4 months. Consultation included.
  - Dermal Fillers: £250. Lip, cheek, and jawline fillers. Results last 6-12 months.
```

---

## 5. Confidence Scoring

Claude is asked to self-report a confidence score (0.0–1.0) after every FAQ response. The threshold for escalation is **0.6**.

**Why 0.6?** Below 0.6 means Claude is inferring more than it's reading from the SOP. At that point, a human agent is more reliable. Above 0.6, the answer is sufficiently grounded in SOP data.

**Limitation:** Self-reported confidence is not perfectly calibrated. It's a useful signal, not a ground truth. In production, this would be supplemented with retrieval-augmented generation (RAG) with similarity scores.

---

## 6. Lead Qualification — Conversational, Not Form-Like

The qualification questions are asked one at a time, embedded naturally in conversation. Claude is instructed to track which questions have been answered from history and not repeat them.

**Why:** A form-like "Q1: ... Q2: ... Q3: ..." approach feels robotic and reduces conversion. Conversational qualification feels like a helpful chat, not an interrogation.

---

## 7. Summary as Structured JSON

The session summary is generated as pure JSON, not natural language. Claude is given the exact schema and instructed to output only valid JSON.

**Why:** The summary is consumed programmatically (logged, sent to CRM, etc.). Natural language summaries are harder to parse reliably. JSON is unambiguous.

---

## 8. Model Choice: claude-sonnet-4-5

`claude-sonnet-4-5` is used for all stages.

**Why:** Sonnet offers the best balance of speed, cost, and instruction-following for this use case. Opus would be overkill for FAQ answering. Haiku may not follow structured output instructions as reliably.

---

## Known Limitations & Future Improvements

- **Confidence calibration:** Self-reported scores need validation against a labelled dataset
- **RAG:** Replace SOP injection with vector search for larger knowledge bases
- **Streaming:** Add streaming responses for better UX in production
- **Session persistence:** Currently in-memory only; would need Redis/DB for multi-session
- **Multi-language:** System prompt is English-only; would need translation layer
