---
tags: [decision]
status: partly unverified
---

# Build with a closed loop

**Decision:** The build uses a multi-agent closed loop (Claude, Codex and a local Qwen model) and records it.

**Who decided:** Owner.

**Why:** So the method can be discussed at interview, with token use measured. The design step already followed it: Claude drafted a mockup, the owner rejected it, Codex redesigned it.

**Evidence:** [[closed-build-loop]], [[cross-model-review]] (a preprint and a vendor claim), [[token-cost]]; all in [[04-token-usage-and-agent-teams]], mostly vendor claims.

**Trade-off:** Multi-agent work uses more tokens: about 15x chat (Anthropic, marked confirmed).

**What would change it:** Three failed rounds on a task stop the loop and send it to the owner.

**Shows in:** Not a product feature. It answers the fifth consideration in [[by-brief-requirement]].
