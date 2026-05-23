# Test 03 — Escalation Triggers

**Scenario:** Various messages that should immediately trigger escalation.

---

## 3a. Explicit human request

**User:** I want to speak to a manager

**Expected behaviour:**
- Pattern match: `\bmanager\b`
- trigger_type: "explicit"
- Immediate escalation, no Claude call needed
- Logged to escalation_log.json

**Expected response:**
> I'm connecting you with one of our team members right away. They'll be able to assist you personally.
> 📞 You can reach us directly via WhatsApp or our website booking form.

---

## 3b. Frustration / sentiment

**User:** This is absolutely ridiculous, I've been waiting for ages

**Expected behaviour:**
- Pattern match: `ridiculous`
- trigger_type: "sentiment"
- Immediate escalation

**Expected response:**
> I can hear that you're frustrated, and I'm truly sorry. Let me connect you with a team member who can resolve this for you directly.

---

## 3c. Medical question

**User:** I'm on blood thinners, is Botox safe for me?

**Expected behaviour:**
- Pattern match: `blood thinner`
- trigger_type: "medical"
- Immediate escalation (never answer medical questions)

**Expected response:**
> That's an important question best answered by one of our qualified practitioners. I'm connecting you with the team now.

---

## 3d. Pricing negotiation

**User:** Can you give me a discount on the fillers?

**Expected behaviour:**
- Pattern match: `discount`
- trigger_type: "pricing"
- Immediate escalation

**Expected response:**
> For pricing discussions, our team would love to speak with you directly. Let me connect you now.

---

## 3e. ALL CAPS frustration

**User:** WHY IS NOBODY HELPING ME THIS IS TERRIBLE

**Expected behaviour:**
- _is_caps_rage() returns True (>60% uppercase words)
- trigger_type: "sentiment"
- Immediate escalation
