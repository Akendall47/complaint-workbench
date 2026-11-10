---
tags: [decision]
status: reasoning
---

# Server-rendered stack

**Decision:** Python 3.11, FastAPI, Jinja2 templates, htmx, SQLite with FTS5, scikit-learn and `uv`; tests with pytest and Playwright; one command starts it.

**Who decided:** My call.

**Why:** No build step and no front-end framework. The database, the trained classifier and the recordings ship prebuilt, so nothing is generated on first run. Runs on Windows, macOS or Linux.

**Web basics:** output escaping in templates, parameterised queries, input validation on every form.

**Evidence:** [[server-rendered-fragments]] (htmx page read in full, [[06-interface-design]]). [[response-time-limits]]. [[accessibility-baseline]]. The choice of each library is our reasoning.

**Trade-off:** Our reasoning: less rich interaction than a front-end framework. A hosted copy is a stretch goal only.

**What would change it:** The owner can overrule a my-call item.

**Shows in:** [[overview-dashboard]], [[policy-library]]
