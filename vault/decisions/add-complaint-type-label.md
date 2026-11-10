---
tags: [decision]
status: reasoning
---

# Add a complaint type label

**Decision:** Each case carries a complaint type beside its department, predicted by a small classifier and shown as filter chips and a complaint map.

**Who decided:** Owner, shaped by my calls. Rejecting a free-floating network graph: my call.

**Why:** The map shows at a glance where each kind of complaint concentrates. A network graph looks striking but values are hard to read from it.

**Evidence:** [[complaint-type]], [[tf-idf-routing-classifier]], [[band-flow-diagram]]. No research source for the map: our reasoning. General chart evidence is in [[07-ux-evidence]].

**Trade-off:** Our reasoning: a second classifier to train and test on synthetic text.

**What would change it:** The owner can overrule a my-call item.

**Shows in:** [[complaint-type-filter]], [[complaint-map]], [[queue-view]], [[departments-view]]
