---
tags: [concept]
status: reasoning
---

# Urgency rules

A case is flagged urgent by stated rules first: deadline close, signs of a vulnerable customer, financial hardship, ongoing fraud, or a case returned before. The classifier's score is a second signal. The flag always shows its reasons. No language model is used. A handler can add or remove the flag, and the change is logged. This is the design author's choice, with no source: our reasoning.

**Where it comes from:** the design document. The deadline and vulnerability inputs draw on [[01-complaint-rules]] (UNVERIFIED there).

**Used in:** [[urgent-by-stated-rules]], [[urgent-flag]], [[queue-view]], [[pipeline-view]]

**Related:** [[complaint-deadlines]], [[vulnerable-customers]], [[cheapest-tool-per-job]], [[returned-case-loop]]
