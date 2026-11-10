---
tags: [feature]
status: partly unverified
---

# Queue view

For the handler: pick the next case, sorted by days left. Urgent cases sort to the top. A returned case comes back at the top. A case below the routing threshold shows "needs routing", and the handler chooses the department first. Complaint type appears as filter chips. Research note 07 supports sortable tables with aids for keeping your place (NN/g, read in full). It also says at most one row should be open at a time (that remark is not marked as read).

**Decisions behind it:** [[dashboard-first-left-navigation]], [[route-with-small-classifier]], [[urgent-by-stated-rules]], [[five-case-states]], [[respond-under-100-ms]]

**Concepts it uses:** [[complaint-deadlines]] (UNVERIFIED limits), [[urgency-rules]], [[tf-idf-routing-classifier]], [[colour-not-alone]], [[response-time-limits]]

**Works with:** [[urgent-flag]], [[complaint-type-filter]]. **Leads to:** [[case-view]]. Evidence: [[07-ux-evidence]]
