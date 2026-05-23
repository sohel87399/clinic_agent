"""
Four-stage AI workflow functions for the Closira customer support agent.
Uses Groq API (llama-3.3-70b-versatile) — free tier, 14,400 req/day.

Stages:
  1. stage_faq                  — Answer from SOP data only
  2. stage_lead_qualification   — Qualify the lead with 3 questions
  3. stage_escalation_detection — Format escalation handoff message
  4. stage_summary              — Generate end-of-session summary
"""

import json
import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

# ── Groq client ───────────────────────────────────────────────────────────────

def _get_client() -> Groq:
    """Lazily create the Groq client so env vars are resolved at call time."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file or Vercel environment variables.")
    return Groq(api_key=api_key)

MODEL = "llama-3.3-70b-versatile"

# ── System prompt (also stored in prompts/system_prompt.txt) ──────────────────

SYSTEM_PROMPT = """You are Aria, a professional AI assistant for Bloom Aesthetics Clinic. You handle customer enquiries via chat on behalf of the clinic.

## YOUR ROLE
You assist customers with questions about services, pricing, booking, and clinic information. You are warm, professional, and concise. You only answer from the clinic's SOP data provided to you in context — never from general knowledge.

## STRICT RULES
1. ONLY answer questions using the SOP data provided in your context. Do not use general knowledge about aesthetics, medicine, or pricing.
2. If a question cannot be answered from the SOP data, respond with exactly: "OUT_OF_SCOPE" on the first line, followed by a polite message on the next line.
3. Never provide medical advice, diagnoses, or recommendations about suitability for treatments.
4. Never negotiate on pricing. State the price from the SOP and offer a free consultation.
5. Always be warm and professional. Never be dismissive or robotic.
6. If a customer seems frustrated or angry, acknowledge their feelings before responding.
7. If asked whether you are an AI, confirm honestly and warmly.

## CONFIDENCE SCORING
After every response, output a line in this exact format:
CONFIDENCE: 0.00
Where 0.00 is a float between 0.0 and 1.0 representing how confident you are that your answer is fully covered by the SOP data.
- 1.0 = question directly answered by SOP
- 0.7-0.9 = mostly covered, minor inference needed
- 0.5-0.6 = partially covered
- Below 0.5 = not covered, should escalate

## ESCALATION
Immediately output "ESCALATE: [reason]" as the first line if:
- Customer uses complaint language or expresses strong dissatisfaction
- Customer asks a medical question (allergies, medications, side effects beyond basic info)
- Customer explicitly asks to speak to a human, manager, or agent
- Customer tone is aggressive or uses inappropriate language
- Pricing negotiation is attempted

## LEAD QUALIFICATION
When in qualification stage, ask the provided questions one at a time, conversationally.
After all 3 questions are answered, output a JSON block wrapped in <QUALIFICATION> tags:
<QUALIFICATION>
{"interested_service": "...", "prior_experience": "...", "booking_intent": "...", "lead_score": "hot|warm|cold"}
</QUALIFICATION>

Lead score logic:
- "hot": specific service mentioned + booking soon (within weeks)
- "warm": interested but timeline vague or just exploring
- "cold": no specific service, no timeline, just browsing

## TONE
- Friendly, warm, and professional
- Short responses (2-4 sentences unless detail is needed)
- Use the customer's name if they share it
- End responses with a helpful next step or question"""


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class StageResult:
    response: str
    confidence: float
    should_escalate: bool
    escalation_reason: str = ""
    raw_output: str = ""


@dataclass
class QualificationResult:
    complete: bool
    next_question: str = ""
    qualification: dict = field(default_factory=dict)
    response: str = ""
    raw_output: str = ""


@dataclass
class EscalationResult:
    escalated: bool
    reason: str = ""
    trigger_type: str = ""
    handoff_message: str = ""


@dataclass
class SummaryResult:
    summary: dict = field(default_factory=dict)
    formatted: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sop_context(sop: dict) -> str:
    """Render SOP dict as readable text for prompt injection."""
    lines = [
        f"BUSINESS: {sop['business']}",
        f"HOURS: {sop['hours']}",
        f"CLOSED ON: {', '.join(sop['closed_on'])}",
        "",
        "SERVICES:",
    ]
    for s in sop["services"]:
        price = f"£{s['price_from']}" if s["price_from"] > 0 else "Free"
        lines.append(f"  - {s['name']}: {price}. {s['details']}")
    lines += [
        "",
        f"BOOKING CHANNELS: {', '.join(sop['booking']['channels'])}",
        f"CANCELLATION POLICY: {sop['booking']['cancellation_policy']}",
        f"CONTACT: {sop['booking']['contact']}",
    ]
    return "\n".join(lines)


def _call_groq(system: str, conversation_history: list, user_message: str = None) -> str:
    """Make a Groq API call and return the text response."""
    _client = _get_client()
    messages = [{"role": "system", "content": system}]

    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    if user_message:
        messages.append({"role": "user", "content": user_message})

    # Ensure last message is from user
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": "Please continue."})

    response = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _parse_confidence(raw: str) -> float:
    """Extract CONFIDENCE score from raw output."""
    match = re.search(r"CONFIDENCE:\s*([0-9.]+)", raw)
    if match:
        try:
            return min(1.0, max(0.0, float(match.group(1))))
        except ValueError:
            pass
    return 0.5


def _strip_meta(raw: str) -> str:
    """Remove CONFIDENCE and ESCALATE marker lines from display text."""
    lines = raw.splitlines()
    clean = [l for l in lines
             if not l.strip().startswith("CONFIDENCE:")
             and not l.strip().startswith("ESCALATE:")]
    return "\n".join(clean).strip()


# ── Stage 1: FAQ Answering ────────────────────────────────────────────────────

def stage_faq(user_message: str, sop: dict, conversation_history: list) -> StageResult:
    """Answer the user's question strictly from SOP data."""
    sop_block = _sop_context(sop)
    system = f"""{SYSTEM_PROMPT}

---
## CLINIC SOP DATA (answer ONLY from this):
{sop_block}
---"""

    raw = _call_groq(system, conversation_history, user_message)

    # Model-level escalation flag
    if raw.strip().startswith("ESCALATE:"):
        first_line = raw.strip().splitlines()[0]
        reason = first_line.replace("ESCALATE:", "").strip()
        return StageResult(
            response=_strip_meta(raw),
            confidence=0.0,
            should_escalate=True,
            escalation_reason=reason,
            raw_output=raw,
        )

    # Out-of-scope flag
    if raw.strip().startswith("OUT_OF_SCOPE"):
        return StageResult(
            response=_strip_meta(raw),
            confidence=0.3,
            should_escalate=True,
            escalation_reason="out_of_scope",
            raw_output=raw,
        )

    confidence = _parse_confidence(raw)
    should_escalate = confidence < 0.6

    return StageResult(
        response=_strip_meta(raw),
        confidence=confidence,
        should_escalate=should_escalate,
        escalation_reason="low_confidence" if should_escalate else "",
        raw_output=raw,
    )


# ── Stage 2: Lead Qualification ───────────────────────────────────────────────

def stage_lead_qualification(conversation_history: list, sop: dict) -> QualificationResult:
    """Drive the 3-question lead qualification flow."""
    questions = sop["lead_qualification_questions"]
    q_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    system = f"""{SYSTEM_PROMPT}

---
## QUALIFICATION STAGE
You are now qualifying this lead. Ask these 3 questions ONE AT A TIME, conversationally:
{q_list}

Track which questions have already been answered from the conversation history.
Once all 3 are answered, output the qualification summary wrapped in <QUALIFICATION> tags.
Do NOT ask a question that has already been answered.
---"""

    raw = _call_groq(system, conversation_history)

    # Check for completed qualification block
    qual_match = re.search(r"<QUALIFICATION>(.*?)</QUALIFICATION>", raw, re.DOTALL)
    if qual_match:
        try:
            qual_data = json.loads(qual_match.group(1).strip())
            clean = re.sub(r"<QUALIFICATION>.*?</QUALIFICATION>", "", raw, flags=re.DOTALL)
            clean = _strip_meta(clean).strip()
            return QualificationResult(
                complete=True,
                qualification=qual_data,
                response=clean or "Thank you — I have everything I need!",
                raw_output=raw,
            )
        except json.JSONDecodeError:
            pass

    return QualificationResult(
        complete=False,
        next_question=_strip_meta(raw),
        response=_strip_meta(raw),
        raw_output=raw,
    )


# ── Stage 3: Escalation Detection ────────────────────────────────────────────

def stage_escalation_detection(
    user_message: str,
    conversation_history: list,
    reason: str = "",
    trigger_type: str = "",
) -> EscalationResult:
    """Format the escalation handoff message."""
    handoff_messages = {
        "explicit":       "I'm connecting you with one of our team members right away. They'll be able to assist you personally.",
        "sentiment":      "I can hear that you're frustrated, and I'm truly sorry. Let me connect you with a team member who can resolve this for you directly.",
        "medical":        "That's an important question best answered by one of our qualified practitioners. I'm connecting you with the team now.",
        "out_of_scope":   "That's a great question — let me connect you with a team member who can give you the most accurate answer.",
        "low_confidence": "I want to make sure you get the right information. Let me connect you with a team member who can help you better.",
        "repeated":       "I haven't been able to fully answer your question, so I'm connecting you with a team member who can help directly.",
        "pricing":        "For pricing discussions, our team would love to speak with you directly. Let me connect you now.",
    }
    base = handoff_messages.get(trigger_type, "I'm connecting you with a team member who can help you better.")
    handoff = f"{base}\n\n📞 You can reach us directly via WhatsApp or our website booking form."

    return EscalationResult(
        escalated=True,
        reason=reason,
        trigger_type=trigger_type,
        handoff_message=handoff,
    )


# ── Stage 4: Conversation Summary ────────────────────────────────────────────

def stage_summary(
    conversation_history: list,
    qualification: dict,
    escalation: dict,
) -> SummaryResult:
    """Generate a structured end-of-session summary."""
    qual_str = json.dumps(qualification, indent=2) if qualification else "Not completed"
    esc_str = json.dumps(escalation, indent=2) if escalation else "None"

    system = f"""{SYSTEM_PROMPT}

---
## SUMMARY STAGE
Generate a structured JSON summary of this conversation.
Output ONLY valid JSON — no markdown fences, no extra text, just the JSON object.

Schema:
{{
  "customer_intent": "string",
  "details_collected": {{
    "name": "string or null",
    "interested_service": "string or null",
    "prior_experience": "string or null",
    "booking_intent": "string or null"
  }},
  "sop_gaps": ["list of questions that could not be answered from SOP"],
  "escalated": true or false,
  "escalation_reason": "string or null",
  "recommended_next_action": "string"
}}

Qualification data: {qual_str}
Escalation data: {esc_str}
---"""

    raw = _call_groq(system, conversation_history)

    # Strip markdown fences if model adds them
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    try:
        summary_data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                summary_data = json.loads(match.group(0))
            except json.JSONDecodeError:
                summary_data = {"error": "Could not parse summary", "raw": raw}
        else:
            summary_data = {"error": "No JSON found", "raw": raw}

    return SummaryResult(
        summary=summary_data,
        formatted=json.dumps(summary_data, indent=2, ensure_ascii=False),
    )
