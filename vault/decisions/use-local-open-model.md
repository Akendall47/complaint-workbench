---
tags: [decision]
status: partly unverified
---

# Use a local open model

**Decision:** The recordings come from an open-weight, Apache-2.0 Qwen model running locally through Ollama.

**Who decided:** Owner (open model, on-prem). The choice of model is my call.

**Why:** To show that customer data never needs to leave the bank's own hardware, and to reduce third-party dependence.

**Evidence:** [[on-premises-model]], [[concentration-risk]], [[least-privilege-model]], all in [[03-on-prem-models-and-retrieval]] and [[02-ai-threats-and-controls]] (UNVERIFIED: secondary sources).

**Trade-off:** A small model may draft weakly. The design names `qwen3:4b-instruct`, already installed; the research note recommends Qwen3.5-9B. If drafts are too weak, the builder pulls a larger Qwen that fits 8 GB of VRAM.

**What would change it:** Weak drafts (stated in the design).

**Shows in:** [[case-view]], [[settings-view]]
