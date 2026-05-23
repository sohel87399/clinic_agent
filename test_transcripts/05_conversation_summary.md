# Test 05 — Conversation Summary

**Scenario:** Full session ends with 'done' — summary is generated.

---

## Full session transcript

**User:** How much are lip fillers?

**Aria:** Our Dermal Fillers start from £250 and cover lip, cheek, and jawline treatments. Results last 6–12 months. We also offer a free initial consultation — would you like to book one?

**[Stage transitions to LEAD_QUALIFICATION]**

**Aria:** While I have you — mind if I ask a couple of quick questions?

**User:** Sure

**Aria:** Which service are you most interested in?

**User:** Lip fillers

**Aria:** Have you had aesthetic treatments before?

**User:** Yes, I had Botox last year

**Aria:** Are you looking to book soon, or just exploring options?

**User:** I'd like to book next week

**[Qualification complete — lead_score: hot]**

**User:** done

**[stage_summary called]**

---

## Expected summary output

```json
{
  "customer_intent": "Customer enquired about lip filler pricing and wanted to book an appointment",
  "details_collected": {
    "name": null,
    "interested_service": "Dermal Fillers (lip fillers)",
    "prior_experience": "Had Botox previously",
    "booking_intent": "Looking to book next week"
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "Book a free consultation for lip fillers — hot lead, follow up within 24 hours"
}
```

---

## Summary with escalation

If session was escalated, expected output:

```json
{
  "customer_intent": "Customer asked about medical suitability for Botox while on medication",
  "details_collected": {
    "name": null,
    "interested_service": "Botox",
    "prior_experience": null,
    "booking_intent": null
  },
  "sop_gaps": ["Is Botox safe while on blood thinners?"],
  "escalated": true,
  "escalation_reason": "Customer asked a medical question requiring practitioner expertise",
  "recommended_next_action": "Human follow-up required — medical question about blood thinners and Botox"
}
```
