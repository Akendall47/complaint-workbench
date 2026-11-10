---
tags: [decision]
status: reasoning
---

# Alert on an unusual rise

**Decision:** A fixed rule raises an alert when complaints about one thing jump. It is not a model.

**Who decided:** Owner asked for the alert. The rule is my call.

**Why:** Many complaints about one thing is a signal. It also serves the firm's duty to find root causes common to types of complaint (DISP 1.3.3R, [[01-complaint-rules]]).

**How:** For each department and complaint type, compare this week with the average of the previous four weeks. Alert when this week is at least twice that average and at least 10 cases. Both numbers live in `pipeline.yaml` ([[one-configuration-file]]). The Overview shows one line with a "View cases" button, only when a rise exists. The seeded demo rise is in General service, Website or app.

**Limit:** The rule finds a rise in volume. It does not find the cause. A person does that.

**Evidence:** Our reasoning. Anyone can check the rule by hand. Small test sets have no rise unless seeded, which the generator only does at 1,000 cases or more.

**Trade-off:** Fixed thresholds miss slow growth and fire on noise in small groups. The 10-case floor is a guard, not a tuned value.

**What would change it:** A bank's real volume pattern.

**Shows in:** [[overview-dashboard]], [[complaint-map]], [[add-complaint-type-label]]
