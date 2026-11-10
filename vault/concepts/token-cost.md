---
tags: [concept]
status: partly unverified
---

# Token cost

Language-model use is measured in tokens read and written. Anthropic reports that agents use about 4x the tokens of chat and multi-agent systems about 15x (marked confirmed in research note 04). Most other figures in that note are vendor or blog claims with no independent benchmark, for example RTK's claimed 60-90% and Caveman's claimed 65% saving. The build records tokens per agent and model from the tools' local logs. A local model costs zero plus electricity.

**Where it comes from:** [[04-token-usage-and-agent-teams]]

**Used in:** [[build-with-closed-loop]], [[use-cheapest-tool-per-job]], [[deliverables-and-cut-order]]

**Related:** [[cheapest-tool-per-job]], [[cross-model-review]], [[closed-build-loop]], [[on-premises-model]]
