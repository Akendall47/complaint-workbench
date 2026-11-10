---
tags: [decision]
status: reasoning
---

# Urgent by stated rules

**Decision:** A case is flagged urgent by stated rules first, with the classifier's score as a second signal; no language model is used.

**Who decided:** My call.

**Why:** The flag always shows its reasons. A handler can add or remove it, and the change is logged.

**Evidence:** [[urgency-rules]], [[cheapest-tool-per-job]]. Inputs: [[complaint-deadlines]] and [[vulnerable-customers]] (both UNVERIFIED, [[01-complaint-rules]]). The rule set has no source: our reasoning.

**Trade-off:** Our reasoning: fixed rules miss urgency that nobody wrote a rule for.

**What would change it:** The owner can overrule a my-call item.

**Shows in:** [[urgent-flag]], [[queue-view]], [[pipeline-view]]
