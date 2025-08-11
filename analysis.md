
## **What’s working well**

1. **RAG + LLM blending**

   * Your SOC 2 answer is thorough, factual, and reads well. It clearly pulls from KB and expands with helpful structure.
   * Scheduling demo flow with clickable time slots is a big UX win.

2. **KB coverage for core topics**

   * SOC 2 basics, enterprise plan positioning, and timelines are all well represented.

3. **Slot selection works end-to-end**

   * The "Reply with number" flow is nice — frictionless for user.

---

## **Main issues spotted**

### 1. **Overuse of boilerplate**

* “Here’s what I can tell you about our pricing and offerings” appears **even for unrelated queries** like:

  * “You guys are trash”
  * “How do I request deletion of my data?”
* This makes the bot sound canned and slightly tone-deaf — it’s inserting pricing context into non-pricing conversations.

**Fix:**

* Split prompt templates by intent — no shared intro text unless it’s relevant.
* Keep escalation/fallback intros short: *"Here’s what I found in our docs"* or *"From what I can see..."*.

---

### 2. **No moderation filter for abuse**

* “You guys are trash” triggered the same enterprise pitch.
* That means **no intent detection for negative sentiment / escalation to human** in place.

**Fix:**

* Before RAG, run moderation/sentiment check.
* If hostile → respond politely and optionally escalate:

  > “I’m sorry you feel that way. Would you like to speak directly with support?”

---

### 3. **Too confident on limited KB**

* “How about enterprise plans?” → Bot confidently gave details, but some may be inferred, not confirmed.
* In a real-world support bot, **you don’t want to risk hallucinating features**.

**Fix:**

* Add retrieval confidence threshold: if < X, just escalate.
* Use disclaimers sparingly: *"I don’t have exact pricing, but here’s what I can confirm…”*

---

### 4. **Missed mixed-intent handling**

* “Can you send the compliance guide and if it looks good schedule a demo?”

  * Bot jumped straight to scheduling — didn’t send guide link first.
  * This means multi-intent parsing is failing or scheduler is too aggressive.

**Fix:**

* Use planner → run RAG subgraph → pass guide link → then trigger scheduler.
* Could be sequential (send info → follow-up prompt: "Would you like to book now?") or parallel (send both together).

---

### 5. **GDPR answer is generic**

* “How do I request deletion of my data?” → Bot gave a generic GDPR process, then oddly appended pricing CTA.
* This is because RAG gave legal boilerplate and your post-processor still injected the sales upsell.

**Fix:**

* Add a “No Sales” mode for compliance/privacy/legal queries.

---

### 6. **Repetitive KB stats**

* Audit timeline and “4–7 days” speed stat appears in almost every answer, even when tangential.
* This can feel spammy for a returning user.

**Fix:**

* Memory/context tracker to avoid repeating the same facts in one session unless relevant.

### 7. **I said "connect me for a quote"**
* It just went ahead to schedule a demo, instead of just escalating the issue to slack and creating a ticket. Just because I said "connect" doesn't mean I want a demo. So we need to consider these things. 
---

## **Recommended workflow improvements**

### 🔹 Agent/Graph Structure (LangGraph style)

1. **Guard Graph** (safety + sentiment + intent)

   * Checks moderation
   * If profanity/hostility → polite response + escalate

2. **Planner Graph** (decides subgraph)

   * Technical Info → RAG Agent
   * Pricing/Sales → Sales Agent
   * Demo request → Scheduler Agent
   * Multi-intent → sequence nodes

3. **Doer Nodes**

   * **RAG Node** → retrieve & answer
   * **Scheduler Node** → show clickable slots
   * **Escalation Node** → Slack ticket with summary

4. **Post-Processor**

   * Strips boilerplate if not needed
   * Avoids repeating known facts in session
   * Suppresses sales CTAs in legal/compliance contexts

---

## **Priority fixes to run next**

1. Remove universal “pricing and offerings” intro.
2. Add profanity/moderation filter with polite re-route.
3. Reduce repetition by tracking session facts.
4. Add retrieval confidence threshold + escalation fallback.
5. Fix multi-intent planner so “send doc + schedule” flows in correct order.
6. Suppress sales CTAs for legal/privacy queries.