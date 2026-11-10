---
tags: [decision]
status: reasoning
---

# Show where the data comes from

**Decision:** Settings has a "Data sources" table, and views link to where their numbers come from.

**Who decided:** Owner. The database notes are my calls.

**Why:** Nobody should act on a figure without knowing its source or age.

**How:** The table lists, for each kind of data, the prototype source, the system a real bank would read it from, whether it holds personal data, and how often it refreshes. Rows: cases and notes, events, policy documents, AI summaries, audit log, staff. The Overview has one "Where these numbers come from" link instead of a link on every card.

**Evidence:** None needed for the prototype side: it is our own schema. The "real bank" column is an assumption about a typical bank, not a description of any actual one, and the deck says so. See [[synthetic-data-only]].

**Trade-off:** The tool reads the bank's systems and writes back only the handover it sends. The audit log accepts new rows only ([[hash-chain-the-audit-log]]). SQLite suits one demo user. A real deployment would use the bank's database with access by role. Our reasoning.

**What would change it:** A real bank's own data map.

**Shows in:** [[settings-view]], [[overview-dashboard]], [[masked-data-with-logged-unmask]]
