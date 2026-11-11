---
tags: [decision]
status: my call, from the vault review
---

# Show the AI summary checks on the Overview

**Decision:** The Overview has a panel "AI summary checks": how many drafted claims had their quote found word for word in the notes, how many are inferences marked for a person to check, and how many have no matching quote and are blocked.

**Who decided:** My call, after a review of this vault against the built screens found no screen that showed whether the AI's drafts were holding up.

**Why:** A team lead needs to see the control working, not only be told it exists. It is also an early warning: if blocked claims rise, the model or the notes have changed. See [[automation-bias]] and [[check-citations-word-for-word]].

**Not done, on purpose:** no per-person version. Counting how often each handler edits the AI would score people, which [[assign-cases-without-scoring-people]] rules out.

**Limit:** in the demo data no handler has confirmed a claim yet, so the panel shows the checks the tool runs, not what people did with them.

**Shows in:** [[overview-dashboard]]
