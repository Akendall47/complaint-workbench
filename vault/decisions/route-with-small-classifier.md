---
tags: [decision]
status: reasoning
---

# Route with a small classifier

**Decision:** Route each complaint to a department with TF-IDF plus logistic regression, once on arrival, and send low-confidence cases to a person.

**Who decided:** Owner (hand-built ML). How routing sits in the flow: my call.

**Why:** It runs in milliseconds on a CPU, costs nothing per case, and shows which words drove the result. The handler can change the department, and the change is logged.

**Evidence:** [[tf-idf-routing-classifier]], [[cheapest-tool-per-job]]. No research note covers the technique: our reasoning. Test: accuracy and per-department results on held-out cases, with a confusion matrix.

**Trade-off:** Trained and tested on [[synthetic-data]]; accuracy will be higher than on real complaints.

**What would change it:** Our reasoning: poor held-out results, or real complaint text.

**Shows in:** [[queue-view]], [[case-view]], [[departments-view]], [[settings-view]]
