---
tags: [decision]
status: reasoning
---

# Record AI answers in advance

**Decision:** The language-model output for every synthetic case is recorded in advance and shipped in the repository; recorded mode is the default.

**Who decided:** Owner. The recording policy is my call.

**Why:** A reviewer must not need a key, an account or a paid service.

**How:** One final run with a fixed prompt version and seed. No case is re-run or hand-picked. The raw output ships. Recorded output passes the same schema validation and citation check as live output.

**Evidence:** [[recorded-ai-output]], [[schema-constrained-output]], [[citation-check]], [[synthetic-data]]. No research source: our reasoning.

**Trade-off:** The reviewer sees stored answers. A live mode calls Ollama when it is running.

**What would change it:** Our reasoning: a reviewer who must see live output can use live mode.

**Shows in:** [[case-view]]
