---
tags: [concept]
status: partly unverified
---

# Schema-constrained output

The model's output is forced to a JSON schema. The server enforces the structure, not the model. Ollama takes a JSON schema in its `format` field and llama.cpp uses GBNF grammars; research note 03 marks both sources as primary but does not say they were read in full. The prototype validates output against the schema at display time. Research note 02 lists schema validation as a control against data leaving through model output.

**Where it comes from:** [[03-on-prem-models-and-retrieval]], [[02-ai-threats-and-controls]]

**Used in:** [[limit-what-the-model-can-do]], [[record-ai-answers-in-advance]], [[case-view]]

**Related:** [[least-privilege-model]], [[citation-check]], [[prompt-injection]], [[on-premises-model]]
