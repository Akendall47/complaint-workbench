---
tags: [concept]
status: reasoning
---

# TF-IDF routing classifier

A small text classifier (TF-IDF plus logistic regression) predicts the department for each complaint. It runs in milliseconds on a CPU, costs nothing per case and can show which words drove the result. Below a confidence threshold the case shows "needs routing" and a person chooses. It is trained and tested on synthetic text, so its accuracy will be higher than on real complaints.

**Where it comes from:** the design document. No research note covers the technique; this is our reasoning. The cost argument draws on [[04-token-usage-and-agent-teams]].

**Used in:** [[route-with-small-classifier]], [[add-complaint-type-label]], [[queue-view]], [[case-view]]

**Related:** [[cheapest-tool-per-job]], [[complaint-type]], [[urgency-rules]], [[synthetic-data]]
