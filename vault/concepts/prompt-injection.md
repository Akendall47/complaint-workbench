---
tags: [concept]
status: partly unverified
---

# Prompt injection

Text written by a customer can carry hidden instructions that a language model follows. OWASP's 2025 list for language models puts prompt injection first (LLM01). The NCSC says models do not separate instructions from data, so it may never be fully mitigated; the aim is to limit the impact. EchoLeak (CVE-2025-32711) was a crafted email that caused zero-click data exfiltration from M365 Copilot. UNVERIFIED: research note 02 was built from search summaries and the pages were not opened.

**Where it comes from:** [[02-ai-threats-and-controls]]

**Used in:** [[limit-what-the-model-can-do]], [[case-view]], [[threats-and-controls]]

**Related:** [[least-privilege-model]], [[adversarial-test-cases]], [[schema-constrained-output]], [[hallucinated-policy]]
