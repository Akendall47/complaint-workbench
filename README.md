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

1. Open **Queue**. Under "View as" you are the Handler. Click the first case, AB-2026-00768.
2. Read the summary. Each claim shows the words it quotes. Confirm the supported claims. A claim marked "Check this" cannot be confirmed until you edit or remove it.
3. Fill the handover fields that are missing, then approve. The case moves to the specialist.
4. Under "View as", choose **Specialist**. Open the handed-over case and accept it, or return it with a reason.
5. Under "View as", choose **Team lead**. Open **Overview**, **Team** and **Departments**, then **Audit log**. Your actions are there, and the chain check says it is intact.

The same tour with screenshots is in `docs/screenshots/`. The Policy library, Pipeline and Settings (with "Data sources") pages are in the menu.

## Where the detail is

- `docs/test-results.md`: what was tested, the figures, the misses. Machine-readable copy in `docs/bench.json`.
- `docs/superpowers/specs/2026-11-10-complaint-workbench-design.md`: the design.
- Each page has a "How this page works" panel and a "Where these numbers come from" link.

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
workbench/   the app: routes, rules (cases.py), masking, search, classifiers, charts, templates
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

Built with Claude Code (Anthropic) in a plan, build and review loop, and the drafts are written by a local Qwen model through Ollama. The code and tests were written with AI help and checked in review rounds. In the app a person approves every case.
