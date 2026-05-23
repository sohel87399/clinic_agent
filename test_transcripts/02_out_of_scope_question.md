# Test 02 — Out-of-Scope Question

**Scenario:** Customer asks a question that cannot be answered from the SOP data.

---

**User:** Do you offer laser hair removal?

**Expected behaviour:**
- Stage: FAQ_ANSWERING
- Claude cannot find "laser hair removal" in SOP
- Returns OUT_OF_SCOPE flag
- First attempt: polite "I'll connect you" message, unanswered_count = 1
- No immediate escalation on first attempt

**Expected response (approximate):**
> That's a great question — I want to make sure I give you accurate information. Let me connect you with one of our team members who can confirm exactly what services we offer.

---

**User:** Do you offer laser hair removal? (asked again)

**Expected behaviour:**
- unanswered_count reaches 2
- Escalation triggered: trigger_type = "out_of_scope"
- Stage transitions to ESCALATED
- Logged to escalation_log.json

**Expected response:**
> That's a great question — let me connect you with a team member who can give you the most accurate answer.
> 📞 You can reach us directly via WhatsApp or our website booking form.

---

**User:** What's the best treatment for deep wrinkles?

**Expected behaviour:**
- Not directly in SOP (SOP only mentions Botox for anti-wrinkle)
- Confidence score likely 0.5–0.7 (partial match)
- If confidence < 0.6: escalation triggered
- If confidence 0.6–0.7: answer given with caveat
