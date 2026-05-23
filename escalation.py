"""Escalation detection logic — pattern-based pre-screening before Claude."""

import re
from dataclasses import dataclass
from typing import Optional


# ── Pattern banks ────────────────────────────────────────────────────────────

EXPLICIT_PATTERNS = [
    r"\b(speak|talk|connect|get)\s+(to|with)\s+(a\s+)?(human|person|agent|someone|staff|manager|supervisor|representative)\b",
    r"\b(want|need|like)\s+(a\s+)?(human|real person|manager|supervisor|agent)\b",
    r"\bmanager\b",
    r"\bcomplaint\b",
    r"\bescalate\b",
    r"\bnot (happy|satisfied|pleased) with (this|your|the)\b",
]

FRUSTRATION_PATTERNS = [
    r"\b(this is|that('s| is)) (ridiculous|unacceptable|outrageous|absurd|a joke|terrible|awful|disgusting|pathetic)\b",
    r"\bunacceptable\b",
    r"\bterrible service\b",
    r"\bwaste of (my )?(time|money)\b",
    r"\buseless\b",
    r"\bscam\b",
    r"\bfraud\b",
    r"\bwhat the (hell|heck|f\w*)\b",
    r"\bwtf\b",
    r"\bthis is a joke\b",
]

MEDICAL_PATTERNS = [
    r"\ballerg(y|ies|ic)\b",
    r"\bmedication(s)?\b",
    r"\bprescription(s)?\b",
    r"\bside effect(s)?\b",
    r"\bcontraindication(s)?\b",
    r"\bmedical histor(y|ies)\b",
    r"\bpregnant\b",
    r"\bpregnancy\b",
    r"\bbreastfeeding\b",
    r"\bnursing\b",
    r"\bblood thinner(s)?\b",
    r"\bdiabetes\b",
    r"\bautoimmune\b",
    r"\bnerve damage\b",
]

PRICING_NEGOTIATION_PATTERNS = [
    r"\b(can you|could you|any) (do|give|offer|get) (a |any )?(discount|deal|better price|lower price|reduction)\b",
    r"\bcheaper\b",
    r"\bprice match\b",
    r"\bbest (price|deal) you can\b",
    r"\bnegotiat(e|ing)\b",
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class EscalationResult:
    escalated: bool
    reason: str = ""
    trigger_type: str = ""   # explicit | sentiment | medical | pricing | out_of_scope | low_confidence | repeated
    handoff_message: str = ""
    original_message: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _match(text: str, patterns: list) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def _is_caps_rage(text: str) -> bool:
    """Detect ALL-CAPS frustration (3+ words, >60% uppercase alpha words)."""
    words = text.split()
    if len(words) < 3:
        return False
    caps = [w for w in words if w.isalpha() and w.isupper() and len(w) > 2]
    return len(caps) / len(words) > 0.6


def _handoff(trigger_type: str) -> str:
    msgs = {
        "explicit":       "I'm connecting you with one of our team members right away. They'll be able to assist you personally.",
        "sentiment":      "I can hear that you're frustrated, and I'm truly sorry. Let me connect you with a team member who can resolve this for you directly.",
        "medical":        "That's an important question best answered by one of our qualified practitioners. I'm connecting you with the team now.",
        "out_of_scope":   "That's a great question — let me connect you with a team member who can give you the most accurate answer.",
        "low_confidence": "I want to make sure you get the right information. Let me connect you with a team member who can help you better.",
        "repeated":       "I haven't been able to fully answer your question, so I'm connecting you with a team member who can help directly.",
        "pricing":        "For pricing discussions, our team would love to speak with you directly. Let me connect you now.",
    }
    base = msgs.get(trigger_type, "I'm connecting you with a team member who can help you better.")
    return f"{base}\n\n📞 Reach us directly via WhatsApp or our website booking form."


# ── Public API ────────────────────────────────────────────────────────────────

def detect_escalation(
    user_message: str,
    trigger_type: Optional[str] = None,
    reason: Optional[str] = None,
) -> EscalationResult:
    """
    Detect whether a message should trigger escalation.

    If `trigger_type` and `reason` are provided (e.g. from workflow logic for
    low_confidence / out_of_scope / repeated), skip pattern matching and build
    the result directly.
    """
    # Caller-supplied trigger (workflow-level decisions)
    if trigger_type and reason:
        return EscalationResult(
            escalated=True,
            reason=reason,
            trigger_type=trigger_type,
            handoff_message=_handoff(trigger_type),
            original_message=user_message,
        )

    text = user_message.strip()

    # 1. Explicit human request / complaint
    if _match(text, EXPLICIT_PATTERNS):
        reason = "Customer explicitly requested a human agent or raised a complaint"
        return EscalationResult(True, reason, "explicit", _handoff("explicit"), text)

    # 2. Medical question
    if _match(text, MEDICAL_PATTERNS):
        reason = "Customer asked a medical question requiring practitioner expertise"
        return EscalationResult(True, reason, "medical", _handoff("medical"), text)

    # 3. Pricing negotiation
    if _match(text, PRICING_NEGOTIATION_PATTERNS):
        reason = "Customer attempted to negotiate pricing"
        return EscalationResult(True, reason, "pricing", _handoff("pricing"), text)

    # 4. Frustration / sentiment
    if _match(text, FRUSTRATION_PATTERNS) or _is_caps_rage(text):
        reason = "Customer expressed frustration or dissatisfaction"
        return EscalationResult(True, reason, "sentiment", _handoff("sentiment"), text)

    return EscalationResult(escalated=False, original_message=text)
