---
tags: [feature]
status: reasoning
---

# Urgent flag

A flag on a case that sorts it to the top of the Queue and sends it down the fast path in the pipeline. It is set by stated rules first, with the classifier's score as a second signal. It always shows its reasons. A handler can remove or add it, and the change is logged. No language model is used. The flag is shown with text, not by colour alone.

**Decisions behind it:** [[urgent-by-stated-rules]], [[use-cheapest-tool-per-job]], [[minimal-style-effective-wins]]

**Concepts it uses:** [[urgency-rules]], [[vulnerable-customers]] (UNVERIFIED), [[complaint-deadlines]] (UNVERIFIED), [[colour-not-alone]]

**Appears in:** [[queue-view]], [[case-view]], [[pipeline-view]]. **Logged in:** [[audit-log-view]]
