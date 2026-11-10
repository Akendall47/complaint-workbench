---
tags: [decision]
status: partly unverified
---

# Guide first-time users

**Decision:** Every view must be easy for a first-time user. The Case view shows one step at a time, and every view has a short "How this page works" panel.

**Who decided:** Owner, after reviewing the mockup on 2026-11-10. The shape of each answer is my call.

**Why:** A reviewer opens the tool cold. A new handler would too.

**How:**
- Case view: one step by default (check the summary, complete the handover, decide). Any step opens at any time and shows its state. The bottom bar names the one next thing to do. A switch shows everything on one screen for experienced handlers.
- "How this page works": a button opens a panel with one sentence of purpose and three or four numbered steps. It is not a tour and never blocks the page.
- Each chart carries one sentence, computed from the data, saying what it shows now.
- The role switcher changes what the Case view offers, not the page. See [[three-roles-with-switcher]].

**Evidence:** [[07-ux-evidence]] supports serving new and expert users together. [[cognitive-forcing]] is why the steps are not skipped.

**Trade-off:** Our reasoning: one step at a time costs an expert some clicks, which is why the one-screen switch exists. Later calm passes cut the Overview further, see [[minimal-style-effective-wins]].

**What would change it:** Watching real handlers use it.

**Shows in:** [[case-view]], [[role-switcher]], [[overview-dashboard]]
