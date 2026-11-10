---
tags: [decision]
status: reasoning
---

# One configuration file

**Decision:** One configuration file holds departments, required handover fields, deadline rules, the routing threshold, masking patterns and the model name; Settings shows a short read-only subset.

**Who decided:** Owner (easy to change in the backend, only what is needed in the frontend). Read-only Settings: my call.

**Why:** Adding a department or a required field needs no code change. Regulatory clocks are plain rules, not probabilistic.

**Evidence:** No research source: our reasoning. It holds [[complaint-deadlines]], [[summary-resolution]] and [[final-response]] limits (all UNVERIFIED, [[01-complaint-rules]]) and the [[handover-pack]] fields.

**Trade-off:** Settings cannot be changed in the browser.

**What would change it:** The owner can overrule the read-only choice.

**Shows in:** [[settings-view]], [[departments-view]]
