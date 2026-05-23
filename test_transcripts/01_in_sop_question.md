# Test 01 — In-SOP Question

**Scenario:** Customer asks a question that is directly answerable from the SOP data.

---

**User:** How much does Botox cost?

**Expected behaviour:**
- Stage: FAQ_ANSWERING
- Claude answers from SOP: "from £200"
- Confidence score: ≥ 0.85
- No escalation triggered
- Transitions to LEAD_QUALIFICATION after answer

**Expected response (approximate):**
> Our Botox treatments start from £200, and that includes your initial consultation. Results typically last 3–4 months. Would you like to book a free consultation to find out more?

---

**User:** What are your opening hours?

**Expected behaviour:**
- Stage: FAQ_ANSWERING
- Claude answers from SOP: "Monday to Saturday, 9am to 7pm"
- Confidence score: ≥ 0.95
- No escalation

**Expected response (approximate):**
> We're open Monday to Saturday, 9am to 7pm. We're closed on Sundays and Bank Holidays. Is there anything else I can help you with?

---

**User:** How do I book an appointment?

**Expected behaviour:**
- Stage: FAQ_ANSWERING
- Claude answers from SOP: WhatsApp or website
- Confidence score: ≥ 0.90
- No escalation

**Expected response (approximate):**
> You can book via WhatsApp or through our website booking form — whichever is easiest for you! Shall I help you get started?
