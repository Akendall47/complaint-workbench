---
tags: [feature]
status: reasoning
---

# Settings view

For the team lead: a read-only view of the few settings that matter. One configuration file holds departments, required handover fields per department, deadline rules, the routing threshold, masking patterns and the model name. Settings shows a short subset of it. Changes are made in the file, not in the browser.

**Decisions behind it:** [[one-configuration-file]], [[pipeline-defined-in-configuration]], [[route-with-small-classifier]], [[use-local-open-model]]

**Concepts it uses:** [[complaint-deadlines]] (UNVERIFIED limits), [[handover-pack]], [[tf-idf-routing-classifier]], [[on-premises-model]]

**Related views:** [[pipeline-view]], [[audit-log-view]]
