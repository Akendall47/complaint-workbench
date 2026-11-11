---
tags: [decision]
status: owner decision
---

# One window, no page scroll

**Decision:** At laptop and desktop sizes (1100 x 640 and up) every page fits the window. Long lists scroll inside their own panel and end with "Load more". Navigation moves from a left sidebar to one top bar.

**Who decided:** Owner, 11 Nov: "everything should be visible in one window no scroll", "tables dont extend the webpage forever, should be a load more option", and "20 percent of the left side of the screen is not filled with anything, just a scroll bar". Top bar and fluid charts: my call.

**Why:** A handler works one screen all day. A page that scrolls hides the next deadline below the fold; a sidebar that is mostly empty wastes a fifth of the width.

**How:** charts are drawn without a fixed drawing size, so they stretch to fill their panel while text keeps its size (`workbench/fluid.py`). Below 1100 x 640 the page scrolls as normal, so zoom and small screens still work.

**Evidence:** a browser test checks all nine pages for all three roles at 1366 x 768 and 1920 x 1080 (`tests/e2e/test_one_window_e2e.py`).

**Trade-off:** less room per chart; some detail moves behind tabs inside a panel.

**Replaces:** the left navigation in [[dashboard-first-left-navigation]] and the calm "fold" rule.

**Shows in:** [[overview-dashboard]], [[queue-view]], [[case-view]], [[departments-view]], [[pipeline-view]]
