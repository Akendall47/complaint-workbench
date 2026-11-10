---
tags: [concept]
status: reasoning
---

# Closed build loop

Per task: write the task, build with tests, run the tests, cross-review, feed failures back, repeat. The loop closes when tests pass and the review is clean. After three failed rounds it stops and goes to the owner. Claude leads, Claude and Codex both build, and a local Qwen model does cheap bounded jobs. Tokens, defects, rounds and time are recorded per round. The method is the owner's requirement; its measurement plan is in research note 04.

**Where it comes from:** [[04-token-usage-and-agent-teams]] (measurement plan), the design document

**Used in:** [[build-with-closed-loop]], [[deliverables-and-cut-order]], [[by-brief-requirement]]

**Related:** [[cross-model-review]], [[token-cost]], [[cheapest-tool-per-job]], [[on-premises-model]]
