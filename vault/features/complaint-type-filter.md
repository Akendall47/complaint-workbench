---
tags: [feature]
status: reasoning
---

# Complaint type filter

Filter chips in the Queue and Departments views that narrow the list to one complaint type. The type is predicted by a small text classifier, with the words that drove the prediction shown. Selecting a type on the complaint map applies the same filter.

**Decisions behind it:** [[add-complaint-type-label]], [[route-with-small-classifier]], [[stated-non-goals]]

**Concepts it uses:** [[complaint-type]], [[tf-idf-routing-classifier]], [[cheapest-tool-per-job]]

**Appears in:** [[queue-view]], [[departments-view]]. **Driven from:** [[complaint-map]]
