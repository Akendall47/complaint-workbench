---
tags: [concept]
status: partly unverified
---

# Least-privilege model

The model is given as little power as possible. Case notes are passed to it as delimited data. It has no tools and no network access. Its output must match a schema, and links and images are stripped from it. The NCSC advises limiting the impact of prompt injection with least privilege, marking data separately, and monitoring (UNVERIFIED: search summary). Prompt-injection classifiers are not relied on: EchoLeak bypassed Microsoft's own classifier (UNVERIFIED: search summary).

**Where it comes from:** [[02-ai-threats-and-controls]]

**Used in:** [[limit-what-the-model-can-do]], [[use-local-open-model]], [[case-view]]

**Related:** [[prompt-injection]], [[schema-constrained-output]], [[adversarial-test-cases]], [[on-premises-model]]
