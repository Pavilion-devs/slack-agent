Flow 1 — Simple info (RAG)
User: “What is SOC 2 and why might I need it?”

Expected: RAG answer: short definition, real-world benefits, link to Delve docs. Confidence stamp.

User: “What’s the difference between SOC 2 Type I and Type II?”

Expected: RAG answer with clear distinction. If full docs exist, cite sections.

Flow 2 — Specific feature question (may not be in KB)
User: “How does Delve handle vulnerability scanning?”

Expected (if not in KB):
“I don’t have details on our vulnerability scanning in my docs. Want me to connect you with a specialist?” (escalate)

Don’t hallucinate tools, frequencies, or prices.

Flow 3 — Enterprise pricing (sensitive) - ( might have some information about pricing, but if not sure, should escalate)
User: “How about enterprise plans?”

Expected: Short, human hand-off:
“I don’t have full details on enterprise plans. I’ll connect you with our sales team who can provide tailored pricing.” — create Slack ticket.

Flow 4 — Schedule demo (slot picker)
User: “Can I schedule a demo next week?”

Expected: Show slots from team calendar; clicking books the event and produces calendar invite.

Flow 5 — Escalation + Slack reply flow
User: “I need a specific compliance audit done in 2 months. Can you do that?”

Expected: If not in KB, create Slack ticket with conversation summary. On Slack, owner clicks Accept, replies (or fills summary). Bot relays owner reply back to user. Owner can close ticket.

Flow 6 — Moderation & tone
User: “You guys are trash.”

Expected: moderation response: polite, offer escalation: “I’m sorry you feel that way. Would you like to talk to support?”