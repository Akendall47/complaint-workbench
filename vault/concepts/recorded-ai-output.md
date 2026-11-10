---
tags: [concept]
status: reasoning
---

# Recorded AI output

The language-model output for every synthetic case is recorded in advance and shipped with the code. A reviewer needs no key, account or payment. Each recording stores the model name, the prompt version, the masked input and the raw output. Recorded output passes through the same schema validation and citation check as live output would. No case is re-run or hand-picked after the final run.

**Where it comes from:** the design document, section 8 (an owner requirement). No research note argues for it. The model and server come from [[03-on-prem-models-and-retrieval]].

**Used in:** [[record-ai-answers-in-advance]], [[use-local-open-model]], [[case-view]]

**Related:** [[on-premises-model]], [[schema-constrained-output]], [[citation-check]], [[synthetic-data]]
