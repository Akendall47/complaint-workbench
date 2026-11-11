---
tags: [decision]
status: owner decision
---

# Act from the Queue, move between cases

**Decision:** The Queue is a work list with a preview: selecting a row shows the case's deadline, urgent reasons, AI summary state and missing handover fields beside the list, with "Open case", "Assign to me" and "Next case". The Case page has tabs for recently opened cases and Previous and Next through the person's own list.

**Who decided:** Owner, 11 Nov: "the queue page shows all complaints but no way to deal with them ... would be nice if there is some action you could take from the queue page" and "the case page could then be toggled to deal with different cases, really think about the user experience". The preview pattern: my call.

**Why:** a handler triages before opening; the preview answers "is this the one to do next" without a page change, and Next keeps them moving down their list without going back.

**Rules kept:** buttons appear only when the rules layer would allow the action ([[person-approves-everything]], [[three-roles-with-switcher]]).

**Shows in:** [[queue-view]], [[case-view]]
