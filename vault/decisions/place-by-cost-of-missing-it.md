---
tags: [decision]
status: partly unverified
---

# Place each section by the cost of missing it

**Decision:** Order content by the cost of missing it, then by how often it is needed. The deadline strip is on the top bar and never a page away.

**Who decided:** Owner asked that every section justify its position. The rule is shaped by my calls.

**Why:** A missed deadline is the costliest error ([[complaint-deadlines]], [[01-complaint-rules]]). Time-critical items sit where they are seen without scrolling at 1440 by 900. Analysis sits lower.

**How:**
- Deadline strip: past deadline, due within 5 business days, urgent. Each count opens the filtered Queue.
- Queue sorted soonest deadline first, so the top row is the next case.
- Case: fixed header with days left, source notes before AI claims, one next action in a fixed bottom bar.
- Audit log: newest first. Left navigation: ordered by frequency of use.

**Changes since the spec:** The strip stays only where it helps, on Queue and Overview. On Case it repeated the header. On Departments, Team and Pipeline it distracted. The Overview was cut to a few figures and one chart.

**Evidence:** [[glanceable-dashboard]], [[left-navigation]]. The reading-order assumption (left to right, top first) is common design guidance and was not checked at a primary source.

**Trade-off:** Our reasoning: less on one screen means more clicks to reach detail.

**What would change it:** A pilot that watches handlers work.

**Shows in:** [[queue-view]], [[overview-dashboard]], [[case-view]], [[dashboard-first-left-navigation]]
