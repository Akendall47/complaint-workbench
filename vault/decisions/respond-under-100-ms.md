---
tags: [decision]
status: verified
---

# Respond in under 100 ms

**Decision:** Server response under 100 ms at the 95th percentile for every view on the synthetic data set.

**Who decided:** Owner (low latency and well-optimised database retrieval).

**Why:** 0.1 s is about the limit for a response to feel instant.

**How:** Indexed columns for every filter. Dashboard figures from single aggregate queries. A benchmark script, with results in the report.

**Evidence:** [[response-time-limits]] (NN/g, read in full, [[06-interface-design]] and [[07-ux-evidence]]). [[server-rendered-fragments]]. Retrieval latency figures found in [[03-on-prem-models-and-retrieval]] were weak, so we measure it ourselves.

**Trade-off:** Our reasoning: the target is only shown on the synthetic data set (at least 120 cases), not at a bank's volume.

**What would change it:** Benchmark results.

**Shows in:** [[queue-view]], [[overview-dashboard]]
