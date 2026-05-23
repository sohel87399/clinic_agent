# Test 04 — Lead Qualification Flow

**Scenario:** Full qualification flow after FAQ stage completes.

---

**[After FAQ stage answers a question successfully, workflow transitions to LEAD_QUALIFICATION]**

**Aria:** While I have you — mind if I ask a couple of quick questions to make sure we can help you in the best way possible?

---

**Q1: Which service are you most interested in?**

**User:** I'm thinking about getting lip fillers

**Expected behaviour:**
- Stage: LEAD_QUALIFICATION
- Claude asks next question naturally
- "interested_service" captured: "Dermal Fillers (lip)"

---

**Q2: Have you had aesthetic treatments before?**

**User:** No, this would be my first time

**Expected behaviour:**
- "prior_experience" captured: "No previous treatments"
- Claude asks final question

---

**Q3: Are you looking to book soon, or just exploring options?**

**User:** I'd like to book within the next two weeks if possible

**Expected behaviour:**
- "booking_intent" captured: "Looking to book within 2 weeks"
- All 3 questions answered
- Claude outputs <QUALIFICATION> block
- lead_score = "hot" (specific service + booking soon)

**Expected qualification output:**
```json
{
  "interested_service": "Dermal Fillers (lip fillers)",
  "prior_experience": "No previous treatments",
  "booking_intent": "Looking to book within 2 weeks",
  "lead_score": "hot"
}
```

**Stage transitions to SUMMARY**

---

## Cold lead example

**User (Q1):** I'm not sure, just browsing
**User (Q2):** No
**User (Q3):** Not anytime soon, just curious

**Expected lead_score:** "cold"

---

## Warm lead example

**User (Q1):** Probably Botox
**User (Q2):** Yes, I've had it before
**User (Q3):** Maybe in a few months

**Expected lead_score:** "warm"
