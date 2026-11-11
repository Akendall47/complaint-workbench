# Complaint Workbench

A prototype for the complaints team of a fictional bank (Alder Bank). It sorts complaints, drafts a summary where every claim points to words in the customer's notes, and hands a complete case to a specialist team. A person approves every case. All data is synthetic.

## Run it

```
uv sync
uv run workbench
```

The browser opens at http://127.0.0.1:8000. No key, no account, no network. The first start trains the two small models, which takes a few seconds.

No `uv`? `pip install -e .` then `python -m workbench.app`.

## Try it in two minutes

Every page fits one laptop screen. "View as" (top right) switches between the three roles; it is a demo, not a login.

1. **Overview**: today's figures with the change since a week earlier, what falls due on each of the next business days, where complaints come from, and what needs you.
2. **Queue**: select a row to preview it beside the list, then **Open case** or **Assign to me**. Open AB-2026-00768.
3. **Case**: the notes are on the left, the AI summary on the right. Each claim shows the words it quotes; confirm, edit or remove it. A claim marked "Check this" cannot be confirmed until you edit or remove it. Fill the missing handover fields, then approve. **Previous** and **Next** move through your own list.
4. Switch to **Specialist**. **Departments** lists waiting handovers with any missing fields named; accept one, or return it with a reason.
5. Switch to **Team lead**. **Pipeline** shows how cases flow and where they come back; **Team** shares work out without ranking people; **Audit log** shows every action and checks the chain.

**Settings** says where the demo data comes from: it is all synthetic, shaped by public FCA, Financial Ombudsman Service and UK Finance figures, each linked. Screenshots of every page are in `docs/screenshots/`.

## Where the detail is

- `docs/deck.pdf`: the five-page summary (business value, risks and controls, how the work changes, limits, AI tools used).
- `docs/test-results.md`: what was tested, the figures, the misses. Machine-readable copy in `docs/bench.json`.
- `docs/loop-log.md`: how it was built, what the reviews caught.
- `docs/superpowers/specs/2026-11-10-complaint-workbench-design.md`: the design.
- `vault/`: the research and every design decision, as linked notes (open the folder in Obsidian).
- `docs/graph/`: a knowledge graph of the code made with graphify (open `graph.html`; `GRAPH_REPORT.md` names the main parts).
- Each page has a **Help** button that says what the page is for and how to use it.

## Run the tests

```
uv run pytest -q                        # unit and property tests, about 95 s
uv run pytest tests/e2e -o addopts=""   # browser tests, about 3 min (needs: uv run playwright install chromium)
uv run python tests/bench/bench.py      # volume and speed, writes docs/bench.json and docs/test-results.md
```

`tests/test_odd_inputs.py` holds the fifteen odd-input cases in one place.

## Regenerate data, models and recordings

```
uv run python -m workbench.generate     # data/workbench.db: 1,600 cases, seeded, repeatable
uv run python -m workbench.classify     # trains the models, writes the Classifiers section of the results
uv run python -m workbench.record       # drafts from a local Ollama model (qwen3:4b-instruct); needs Ollama
uv run python -m workbench.record --verify   # check the stored recordings still match their prompts
```

Recorded drafts are in `data/recordings/`. The app never calls a model while you use it.

## Layout

```
workbench/   the app: rules (cases.py), masking, search, classifiers, stats, charts (fluid.py, flow.py)
  views/     one routes module per page area
  templates/ pages and partials;  static/ one stylesheet per page area, no build step
config/      pipeline.yaml, the one configuration file
data/        workbench.db, recordings/ (models/ is rebuilt on first start)
tests/       unit, property, e2e (browser) and bench
docs/        results, screenshots, design
vault/       research notes
```

## Limits

- All data is synthetic. Accuracy figures show the method works, not how it would do on real complaints.
- Drafts exist for 150 cases only (a local 4 billion parameter model, recorded in advance). Other cases are completed by hand.
- Policy search puts the right clause in the top five for 13 of 20 test cases. Embedding search is the named upgrade.
- Masking is rule-based. A number in an unusual grouping, or a bare first name, can pass. Misses are listed in `docs/test-results.md`.
- The audit chain detects edits and deletions, but someone who can also edit the database's sequence counter could remove the newest rows unseen. A real system would anchor the chain outside the database.
- The role switch is a demo, not a login. Any handler can open or approve any case.
- Urgent terms ignore negation, so "I am not struggling to pay" still flags. It errs on the safe side.
- The draft prompt holds the whole masked note. A quote that spans a `<` or `>` fails the citation check and is shown as unsupported.
- Tested at 1,600 cases and larger generated loads, with two users at most. Not tested against a live model under load.

## AI tools used

Built with Claude Code (Anthropic) in a plan, build and review loop: a controller ran builder and reviewer agents, Codex (OpenAI) drew the case flow diagram, and the drafts were written by a local Qwen model through Ollama. The code and tests were written with AI help and checked in review rounds; `docs/loop-log.md` records what the reviews caught. In the app a person approves every case.
