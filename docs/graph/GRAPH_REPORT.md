# Graph Report - workbench  (2026-11-11)

## Corpus Check
- Corpus is ~35,548 words - fits in a single context window. You may not need a graph.

## Summary
- 707 nodes · 1777 edges · 28 communities (23 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- htmx Vendored Library
- Case Actions
- Charts and Case Flow
- Case Page Partials
- Complaint Classifier
- Drafts and Citations
- App Routes and Guards
- Page Content Config
- Dashboard Statistics
- App Shell
- Database and Data Generator
- Department Queries
- Audit Hash Chain
- Deadlines and Business Days
- Case View and Handover
- Base Layout
- Settings and Data Sources
- Departments Page
- Overview Page
- Pipeline Page
- Audit Page
- Help and Policies
- Case Page Navigation
- Team Page
- Source Link Macro

## God Nodes (most connected - your core abstractions)
1. `current_actor()` - 30 edges
2. `e()` - 29 edges
3. `ne()` - 28 edges
4. `se()` - 27 edges
5. `ue()` - 27 edges
6. `De()` - 27 edges
7. `overview()` - 27 edges
8. `create_app()` - 26 edges
9. `_do()` - 23 edges
10. `db()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `overview()` --calls--> `edge_of()`  [INFERRED]
  views/overview.py → app.py
- `more_attention()` --calls--> `db()`  [INFERRED]
  views/overview.py → app.py
- `overview()` --calls--> `db()`  [INFERRED]
  views/overview.py → app.py
- `departments()` --calls--> `db()`  [INFERRED]
  views/work.py → app.py
- `more_handovers()` --calls--> `db()`  [INFERRED]
  views/work.py → app.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Case panel composition** — templates_partials_case_main, templates_partials_claims, templates_partials_handover, templates_partials_decide, templates_partials_notes [EXTRACTED 1.00]

## Communities (28 total, 5 thin omitted)

### Community 0 - "htmx Vendored Library"
Cohesion: 0.08
Nodes (100): A(), ae(), an(), at(), B(), be(), bn(), bt() (+92 more)

### Community 1 - "Case Actions"
Cohesion: 0.08
Nodes (54): accept(), fn(), add_claim(), fn(), approve(), fn(), assign(), fn() (+46 more)

### Community 2 - "Charts and Case Flow"
Cohesion: 0.06
Nodes (32): _e(), _box(), case_flow(), _e(), _link(), _near(), _place(), _text() (+24 more)

### Community 3 - "Case Page Partials"
Cohesion: 0.05
Nodes (44): Cases needing attention list, Load more (hx-get /overview/attention), Bottom bar next action (#bar-text), Next step / Go to decide button, Change department form (POST /cases/ID/department), History trail dropdown, Change urgency form (POST /cases/ID/urgent), Case panel (#case, htmx swap target) (+36 more)

### Community 4 - "Complaint Classifier"
Cohesion: 0.07
Nodes (23): apply_to_cases(), build(), ensure_models(), _evaluate(), looks_english(), main(), _norm_text(), _note1() (+15 more)

### Community 5 - "Drafts and Citations"
Cohesion: 0.07
Nodes (25): _norm(), quote_in_source(), clean(), known_values(), load_handover(), masked_notes(), parse(), _raw_output() (+17 more)

### Community 6 - "App Routes and Guards"
Cohesion: 0.08
Nodes (35): create_app(), alerts(), db(), edge_of(), failed(), from_this_app(), guard(), page() (+27 more)

### Community 7 - "Page Content Config"
Cohesion: 0.05
Nodes (41): layout_reason, purpose, steps, cards, queue, layout_reason, purpose, steps (+33 more)

### Community 8 - "Dashboard Statistics"
Cohesion: 0.07
Nodes (15): by_source(), by_type(), department_table(), headline(), headline_change(), _open_by(), returned_by_handler(), rise_pairs() (+7 more)

### Community 10 - "Database and Data Generator"
Cohesion: 0.12
Nodes (16): connect(), init_db(), _ago(), _complaint(), _customer(), _details_c(), fdate(), generate() (+8 more)

### Community 11 - "Department Queries"
Cohesion: 0.14
Nodes (17): Actor, missing_fields(), department_figures(), department_rows(), handovers(), missing_by_field(), _slice(), current_actor() (+9 more)

### Community 12 - "Audit Hash Chain"
Cohesion: 0.23
Nodes (6): append(), describe(), _hash(), now(), set_clock(), verify_chain()

### Community 13 - "Deadlines and Business Days"
Cohesion: 0.30
Nodes (7): add_business_days(), business_days_left(), deadline_for(), due_soon_edge(), _is_business(), due_by_day(), team_figures()

### Community 14 - "Case View and Handover"
Cohesion: 0.24
Nodes (5): build(), _detail(), money_text(), split_note(), can_decide()

### Community 15 - "Base Layout"
Cohesion: 0.22
Nodes (7): Footer synthetic-data notice, Help button, Vendored htmx 2.0.4 (no network), Main nav, Role switch form (POST /role, htmx), Case not found notice, Demo role switch notice (not a login)

### Community 16 - "Settings and Data Sources"
Cohesion: 0.22
Nodes (7): Assumptions without public source, Public data sources table, Pipeline rules list, Add a test complaint form (POST /intake), Where the data comes from section, Model and prompt version panel, Settings rules (routing threshold, deadlines, rise, urgent)

### Community 17 - "Departments Page"
Cohesion: 0.29
Nodes (6): Department filter chips, Department KPI figures, Open cases tabs (channel, type, missing fields), Waiting handovers panel, Today KPIs, Team KPI figures

### Community 18 - "Overview Page"
Cohesion: 0.29
Nodes (6): AI summary checks panel, Complaint map, Deadlines approaching panel, New complaints trend tabs, Unusual rise banner, Workload tabs

### Community 19 - "Pipeline Page"
Cohesion: 0.29
Nodes (5): By stage panel, Alerts toggle (hx-post /prefs/alerts), Deadline pills strip (past, soon, urgent, rises), By stage panel, Case flow chart

### Community 20 - "Audit Page"
Cohesion: 0.33
Nodes (4): Audit hash-chain status chip, Audit entries table and filters, Team lead only gate, Load older (hx-get audit rows)

### Community 21 - "Help and Policies"
Cohesion: 0.33
Nodes (4): help_panel macro (page help popover), Clause list, Policy clause search, Policy sections list

### Community 22 - "Case Page Navigation"
Cohesion: 0.40
Nodes (3): Case detail page, Previous/Next within queue order, Recently opened cases list

### Community 24 - "Team Page"
Cohesion: 0.50
Nodes (3): Needs attention list, Unassigned cases panel, Team workload table

## Knowledge Gaps
- **60 isolated node(s):** `Main nav`, `Help button`, `Vendored htmx 2.0.4 (no network)`, `Footer synthetic-data notice`, `Audit hash-chain status chip` (+55 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 232 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `current_actor()` connect `Department Queries` to `App Shell`, `Charts and Case Flow`, `App Routes and Guards`, `Case Actions`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `e()` (e.g. with `htmx.min.js` and `an()`) actually correct?**
  _`e()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Main nav`, `Help button`, `Vendored htmx 2.0.4 (no network)` to the rest of the system?**
  _60 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `htmx Vendored Library` be split into smaller, more focused modules?**
  _Cohesion score 0.07748319641523525 - nodes in this community are weakly interconnected._
- **Why does `create_app()` connect `App Routes and Guards` to `Case Actions`, `Charts and Case Flow`, `Complaint Classifier`, `Drafts and Citations`, `App Shell`, `Database and Data Generator`, `Department Queries`, `Audit Hash Chain`, `Deadlines and Business Days`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Should `Case Actions` be split into smaller, more focused modules?**
  _Cohesion score 0.07507914970601538 - nodes in this community are weakly interconnected._
- **Why does `overview()` connect `Charts and Case Flow` to `App Routes and Guards`, `Dashboard Statistics`, `App Shell`, `Department Queries`, `Deadlines and Business Days`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._