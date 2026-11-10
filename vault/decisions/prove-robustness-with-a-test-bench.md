---
tags: [decision]
status: reasoning
---

# Prove robustness with a test bench

**Decision:** Test the design against volume, odd inputs and generated inputs, and publish what happened, including failures.

**Who decided:** Owner asked. The contents are my calls.

**Why:** A demo on a clean data set shows little. The owner wanted evidence that it holds up to thousands of complaints and odd situations.

**How:**
- Volume: the generator takes a size. Record build time, search time and page times against the 100 ms target ([[respond-under-100-ms]]) and report the size where it is missed.
- Odd inputs, one test each with the expected result stated: empty text, very long text, not English, text that gives the model orders, unusual personal-detail formats, duplicates, ties between departments, weekends and bank holidays, double returns, bad citations, invalid model output, two people acting at once, edits to the audit log. See [[adversarial-test-cases]].
- Property-based tests for masking, deadlines and the citation check ([[pii-masking]], [[citation-check]]).
- Classifier accuracy on held-out data, with the share sent to "needs routing". The figures are on synthetic data and show the method works, not how it would do on real complaints.

**Not tested:** Real complaints, real handlers, many users at once, and a live model under load.

**Evidence:** Results are in `docs/test-results.md`. The loop log records how the test suite itself needed fixing: see `docs/loop-log.md`.

**Trade-off:** Our reasoning: synthetic tests can only show the design is sound, not that it is right for a bank.

**What would change it:** A pilot on real, approved data.

**Shows in:** [[pipeline-view]], [[synthetic-data-only]], [[verify-before-quoting]]
