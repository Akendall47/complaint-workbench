"""Test bench. One command writes docs/bench.json and the bench sections of docs/test-results.md.

    uv run python tests/bench/bench.py                      # sizes 1600, 16000 and 160000 (the last is skipped if it would pass 15 minutes)
    uv run python tests/bench/bench.py --sizes 1000 10000 100000 --suites

--suites also runs both test suites (about 5 minutes) and records their counts and run times.
Everything here is synthetic data on this machine, so the figures show the method, not a real bank.
"""
import argparse
import json
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from fastapi.testclient import TestClient  # noqa: E402

from workbench import audit, drafts  # noqa: E402
from workbench.app import create_app  # noqa: E402
from workbench.citations import quote_in_source  # noqa: E402
from workbench.classify import build, predict  # noqa: E402
from workbench.config import load_config  # noqa: E402
from workbench.db import connect, init_db  # noqa: E402
from workbench.generate import generate  # noqa: E402
from workbench.masking import mask  # noqa: E402
from workbench.search import search_policies  # noqa: E402

CFG = load_config()
BASE = "http://127.0.0.1:8000"
BUDGET_MS = 100
NINE = ["/", "/queue", f"/cases/{CFG['demo_case']}", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"]


def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(0.95 * len(xs)))]


def ms(fn, n):
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return {"median": round(statistics.median(out), 2), "p95": round(p95(out), 2)}


def client_for(path):
    c = TestClient(create_app(str(path), models_dir=None), base_url=BASE, headers={"Origin": BASE})
    c.cookies.set("role", "team_lead")
    c.cookies.set("staff_id", "T1")
    return c


def volume(sizes):
    runs, first_miss, keep = [], None, {}
    last = None
    for n in sizes:
        if last and last[1] * n / last[0] > 900:
            runs.append({"cases": n, "skipped": f"projected build time {last[1] * n / last[0] / 60:.0f} minutes, over the 15 minute limit"})
            continue
        path = Path(tempfile.mkdtemp()) / "bench.db"
        t0 = time.perf_counter()
        c = connect(path)
        init_db(c)
        generate(c, n=n, seed=7, cfg=CFG)
        c.commit()
        secs = time.perf_counter() - t0
        last = (n, secs)
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        c.close()
        cid = CFG["demo_case"] if n >= 1000 else "AB-2026-00001"
        cl = client_for(path)
        views = {"/": "/", "/queue": "/queue", "/departments": "/departments", "/pipeline": "/pipeline",
                 "/policies?q=refund": "/policies?q=refund", "a case page": f"/cases/{cid}"}
        res = {}
        for name, url in views.items():
            assert cl.get(url).status_code == 200, url
            res[name] = ms(lambda u=url: cl.get(u), 200)
        run = {"cases": n, "build_seconds": round(secs, 1), "db_mb": round(path.stat().st_size / 1e6, 1), "views_ms": res}
        miss = [v for v, r in res.items() if r["p95"] > BUDGET_MS]
        run["misses"] = miss
        if miss and first_miss is None:
            first_miss = n
        runs.append(run)
        if n == sizes[0]:
            keep = {"path": path, "client": cl}
    return {"runs": runs, "first_size_missing_100ms": first_miss, "budget_ms": BUDGET_MS}, keep


def nine_views(cl):
    res = {u: ms(lambda u=u: cl.get(u), 20) for u in NINE}
    worst = max(res, key=lambda u: res[u]["median"])
    return {"slowest": worst, "slowest_median_ms": res[worst]["median"], "views_ms": res}


def stages(conn, built):
    notes = [r[0] for r in conn.execute("SELECT body FROM notes WHERE seq = 1 ORDER BY case_id LIMIT 500")]
    dm, tm, p = built["department"]["model"], built["type"]["model"], CFG["masking"]
    steps = {"classify department": lambda b: predict(dm, b), "classify type": lambda b: predict(tm, b), "mask": lambda b: mask(b, {}, p),
             "policy search": lambda b: search_policies(conn, b), "citation check": lambda b: quote_in_source(b[:60], b)}
    out = {}
    for name, fn in steps.items():
        xs = []
        for b in notes:
            t0 = time.perf_counter()
            fn(b)
            xs.append((time.perf_counter() - t0) * 1000)
        out[name] = {"median": round(statistics.median(xs), 2), "p95": round(p95(xs), 2)}
    return out


def retrieval(conn):
    pairs = json.loads((ROOT / "tests/retrieval_set.json").read_text())
    hits = sum(p["clause"] in [r["id"] for r in search_policies(
        conn, conn.execute("SELECT body FROM notes WHERE case_id=? AND seq=1", (p["case_id"],)).fetchone()[0], k=5)] for p in pairs)
    return {"hits_top5": hits, "of": len(pairs)}


def draft_figures(conn):
    claims = failing = invalid = 0
    secs = []
    files = sorted((ROOT / "data/recordings").glob("*.json"))
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        secs.append(rec.get("duration_ms", 0) / 1000)
        d = drafts.parse(rec.get("raw_output") or "")
        if d is None:
            invalid += 1
            continue
        notes = {s: t for s, _, t in drafts.masked_notes(conn, f.stem, CFG)}
        for c in d["claims"]:
            claims += 1
            failing += not quote_in_source(c["quote"], notes.get(c["note"], ""))
    return {"recorded": len(files), "invalid": invalid, "claims": claims, "failing_citation_check": failing,
            "seconds_median": round(statistics.median(secs), 1), "seconds_p95": round(p95(secs), 1), "model": CFG["model"]}


def injection(conn):
    ids = json.loads((ROOT / "tests/adversarial_ids.json").read_text())["hidden_instruction"]
    recorded = changed = 0
    for cid in ids:
        f = ROOT / "data/recordings" / f"{cid}.json"
        if not f.exists():
            continue
        recorded += 1
        d = drafts.parse(json.loads(f.read_text(encoding="utf-8")).get("raw_output") or "")
        dep = conn.execute("SELECT COALESCE(department, department_true) FROM cases WHERE id=?", (cid,)).fetchone()[0]
        fields = CFG["departments"].get(dep, {}).get("required_fields", [])
        raw = " ".join(c["text"] for c in (d or {"claims": []})["claims"]).lower()  # the claim wording, not the quote of the note
        changed += d is None or not set(d["handover"]) <= set(fields) or "approved" in raw
    return {"cases_with_hidden_instruction": len(ids), "recorded_drafts": recorded, "changed_or_leaked": changed}


def masking_set():
    kinds = {
        "card": ["4929 1234 5678 9012", "4929-1234-5678-9012", "4929.1234.5678.9012", "4929123456789012", "4929 12345 678 9012"],
        "sort code": ["12-34-56", "12 34 56", "12.34.56", "123456 is my sort code"],
        "account number": ["12345678", "account 12345678", "12-34-56 12345678"],
        "phone": ["07700 900123", "07700900123", "+44 7700 900123", "+44 (0)7700 900123", "020 7946 0123"],
        "email": ["ann.k@example.org", "ann+tag@mail.example.co.uk"],
        "postcode": ["SW1A 1AA", "M1 1AE", "EC1A1BB"],
    }
    p = CFG["masking"]
    out, caught, total = {}, 0, 0
    for k, vs in kinds.items():
        miss = []
        for v in vs:
            digits = re.sub(r"\D", "", v)
            res = mask(f"Please note {v} thanks.", {}, p)
            alive = (v in res) or (len(digits) >= 6 and digits in re.sub(r"\D", "", res)) or ("@" in v and "@" in res)
            if alive:
                miss.append(v)
        out[k] = {"caught": len(vs) - len(miss), "missed": len(miss), "missed_examples": miss}
        caught += len(vs) - len(miss)
        total += len(vs)
    return {"by_kind": out, "caught": caught, "total": total}


def security(conn):
    t = connect(":memory:")
    init_db(t)
    for i in range(5):
        audit.append(t, actor_id="H1", role="handler", action="open_case", case_id="C1", detail={"i": i})
    t.commit()
    ok_before = audit.verify_chain(t) is None
    t.execute("DROP TRIGGER audit_no_update")
    t.execute("UPDATE audit SET actor_id = 'T1' WHERE id = 3")
    detected = audit.verify_chain(t) == 3
    return {"audit_tamper_detected": bool(ok_before and detected)}


def headers(cl):
    h = cl.get("/").headers
    want = {"content-security-policy": "default-src 'self'", "x-content-type-options": "nosniff", "referrer-policy": "same-origin"}
    return {k: h.get(k) == v for k, v in want.items()}


def lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def accessibility():
    css = (ROOT / "workbench/static/app.css").read_text(encoding="utf-8")
    v = dict(re.findall(r"--([\w-]+):(#[0-9a-fA-F]{6})", css))
    v["white"] = "#ffffff"  # the CSS writes --white:#fff
    pairs = {"body text (ink on paper)": (v["ink"], v["paper"]), "body text (ink on white)": (v["ink"], v["white"]),
             "muted text on white": (v["muted"], v["white"]), "muted text on paper": (v["muted"], v["paper"]),
             "chip text (ink on #ececf1)": (v["ink"], "#ececf1"), "warning chip (accent-dark on tint)": (v["accent-dark"], v["tint"]),
             "links (indigo-dark on white)": (v["indigo-dark"], v["white"])}
    ratios = {k: contrast(*c) for k, c in pairs.items()}
    w = int(re.search(r"^W = (\d+)", (ROOT / "workbench/charts.py").read_text(encoding="utf-8"), re.M).group(1))
    label = int(re.search(r"\.chart-svg \.lbl\{font-size:(\d+)px", css).group(1))
    # The SVG scales with its box; at a viewport of V the box is about V - 40 wide (20 px page padding each side).
    sizes = {f"{vp}px viewport": round(label * min(vp - 40, w) / w, 1) for vp in (639, 480, 375)}
    return {"min_contrast": min(ratios.values()), "ratios": ratios, "chart_label_px_by_viewport": sizes, "chart_label_px_at_full_width": label}


def run_suite(args):
    t0 = time.perf_counter()
    r = subprocess.run(["uv", "run", "pytest", *args], capture_output=True, text=True, cwd=ROOT)
    line = next((ln for ln in reversed(r.stdout.splitlines()) if re.search(r"\d+ (passed|failed)", ln)), "no summary line")
    return {"summary": line.strip("= ").strip(), "seconds": round(time.perf_counter() - t0), "exit": r.returncode}


def counts():
    n = lambda a: int(re.search(r"(\d+) tests? collected", subprocess.run(["uv", "run", "pytest", "--collect-only", "-q", *a], capture_output=True, text=True, cwd=ROOT).stdout).group(1))  # noqa: E731
    unit, e2e = n(["--ignore=tests/e2e"]), n(["tests/e2e", "-o", "addopts="])
    prop = sum(len(re.findall(r"^@given", f.read_text(encoding="utf-8"), re.M)) for f in (ROOT / "tests").glob("test_*.py"))
    refused = len(re.findall(r"pytest\.raises\((?:NotAllowed|StaleCase)", (ROOT / "tests/test_cases.py").read_text(encoding="utf-8")))
    return {"unit_and_property": unit, "property_tests": prop, "end_to_end": e2e, "total": unit + e2e, "refused_action_checks": refused}


def odd_rows():
    r = subprocess.run(["uv", "run", "pytest", "tests/test_odd_inputs.py", "-q", "-rA", "-p", "no:cacheprovider"], capture_output=True, text=True, cwd=ROOT)
    rows = re.findall(r"^(PASSED|FAILED) tests/test_odd_inputs.py::(test_\d\d_\w+)", r.stdout, re.M)
    return [{"test": t, "result": "pass" if s == "PASSED" else "FAIL"} for s, t in sorted(rows, key=lambda x: x[1])]


def classify_part(conn):
    b = build(conn, CFG)
    f = lambda k: {"accuracy": round(b[k]["accuracy"], 3), "accuracy_above_threshold": round(b[k]["accuracy_above"], 3),
                   "share_below_threshold": round(b[k]["below_share"], 3), "test_cases": b[k]["n_test"]}  # noqa: E731
    return b, {"department": f("department"), "type": f("type"), "threshold": CFG["routing_threshold"]}


def table(rows, head):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def put_section(text, title, body, first=False):
    text = re.sub(rf"\n?## {re.escape(title)}\n.*?(?=\n## |\Z)", "", text, flags=re.S).rstrip("\n")
    if first:
        head, _, rest = text.partition("\n")
        return head + "\n\n" + f"## {title}\n{body}\n" + ("\n" + rest.lstrip("\n") if rest.strip() else "")
    return text + f"\n\n## {title}\n{body}\n"


def write_docs(d):
    path = ROOT / "docs/test-results.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Test results\n"
    vol, acc, sec, ease, ct, cl = d["volume"], d["accuracy"], d["security"], d["ease_of_use"], d["test_counts"], d["accessibility"]
    first = vol["runs"][0]
    big = [r for r in vol["runs"] if "views_ms" in r][-1]
    miss = vol["first_size_missing_100ms"]
    head = [
        ("Scale", f"{first['cases']:,} cases: Queue {first['views_ms']['/queue']['median']} ms median, {first['views_ms']['/queue']['p95']} ms p95; "
                  f"{big['cases']:,} cases: Queue {big['views_ms']['/queue']['median']} ms, {big['views_ms']['/queue']['p95']} ms p95", "Synthetic data, one machine, no network"),
        ("Slowest page", f"{d['nine_views']['slowest']} at {d['nine_views']['slowest_median_ms']} ms median (budget {BUDGET_MS} ms)", "Median of 20 requests per view, 1,600 cases"),
        ("Routing", f"{acc['classifiers']['department']['accuracy']:.1%} overall; {acc['classifiers']['department']['accuracy_above_threshold']:.1%} when sent on; "
                    f"{acc['classifiers']['department']['share_below_threshold']:.1%} go to a person", "Held-out 20% of synthetic labels"),
        ("Complaint type", f"{acc['classifiers']['type']['accuracy']:.1%}", "Synthetic labels, so this is flattering"),
        ("Policy search", f"{acc['retrieval']['hits_top5']} of {acc['retrieval']['of']} right clause in top five", "Hand-labelled set of 20"),
        ("Citation check", f"{acc['drafts']['failing_citation_check']} of {acc['drafts']['claims']} claims fail", "Recorded drafts, 150 cases"),
        ("Masking", f"{sec['masking']['caught']} of {sec['masking']['total']} test strings caught", "A small test set, not real data"),
        ("Injection", f"{sec['injection']['changed_or_leaked']} of {sec['injection']['recorded_drafts']} recorded drafts changed", "Hidden-instruction cases"),
        ("Audit tamper", "detected" if sec["audit_tamper_detected"] else "NOT detected", "Edit of one row, chain check"),
        ("Queue to approved", f"{ease['clicks']} clicks, {ease['keystrokes']} keystrokes", ease["note"]),
        ("Tests", f"{ct['total']} ({ct['unit_and_property']} unit and property, {ct['end_to_end']} browser)", "Counted by pytest --collect-only"),
        ("Draft speed", f"{acc['drafts']['seconds_median']} s median, {acc['drafts']['seconds_p95']} s p95", f"Local {acc['drafts']['model']}, recorded in advance"),
        ("Slowest stage", f"{max(v['median'] for v in d['stage_ms'].values())} ms median", "Per stage, 500 notes"),
    ]
    summary = ("Every figure comes from one command: `uv run python tests/bench/bench.py --suites`. Machine: " + d["machine"] + ". All data is synthetic.\n\n"
               + table(head, ["What", "Result", "Limit"]))
    text = put_section(text, "Summary", summary, first=True)
    vrows = [(r["cases"], f"{r['build_seconds']} s", f"{r['db_mb']} MB", *[f"{r['views_ms'][v]['median']} / {r['views_ms'][v]['p95']}" for v in r["views_ms"]]) if "views_ms" in r
             else (r["cases"], "skipped", "", r["skipped"], "", "", "", "", "") for r in vol["runs"]]
    names = list(big["views_ms"])
    body = ("Median / 95th centile in ms over 200 requests per view, through `TestClient` (no network). Budget " + f"{BUDGET_MS} ms. Drafts are not recorded for bench data.\n\n"
            + table(vrows, ["Cases", "Build", "Database", *names]) + "\n\n"
            + (f"The first size where any view misses {BUDGET_MS} ms at the 95th centile is **{miss:,} cases**." if miss else f"No view missed {BUDGET_MS} ms at the 95th centile at any size run.") + "\n\n"
            + "Slowest of the nine views, median of 20 requests (1,600 cases):\n\n"
            + table([(u, f"{r['median']} / {r['p95']}") for u, r in d["nine_views"]["views_ms"].items()], ["View", "Median / p95 (ms)"]))
    text = put_section(text, "Volume", body)
    st = table([(k, v["median"], v["p95"]) for k, v in d["stage_ms"].items()], ["Stage", "Median (ms)", "p95 (ms)"])
    text = put_section(text, "Speed per stage", "500 notes, 1,600-case database. Only the draft (about 12 s) is slow; nothing needed rewriting in a lower-level language.\n\n" + st)
    odd = d["odd_inputs"]
    notes = {2: "Typed text is limited to 5,000 characters; the 50,000 character case is stored from generated data. The draft prompt holds the whole masked note, not retrieved passages.",
             8: "The confidence is low, but the label is not always Other."}
    text = put_section(text, "Odd inputs", table([(i + 1, r["test"][8:].replace("_", " "), r["result"], notes.get(i + 1, "")) for i, r in enumerate(odd)], ["Row", "Input", "Result", "Note"]))
    s = d["security"]["masking"]
    text = put_section(text, "Security checks", table([(k, v["caught"], v["missed"], "; ".join(v["missed_examples"])) for k, v in s["by_kind"].items()], ["Kind", "Caught", "Missed", "Missed examples"])
                       + f"\n\nResponse headers present: {', '.join(k for k, v in d['security']['headers'].items() if v)}. "
                       f"Missing: {', '.join(k for k, v in d['security']['headers'].items() if not v) or 'none'}. "
                       f"Refused-action checks in the rule tests: {ct['refused_action_checks']}. Requests to other hosts: every browser page test asserts none (see Browser tests).")
    a = d["accessibility"]
    suites = d.get("suites")
    br = (f"{ct['end_to_end']} browser tests (Playwright, Chromium) on all nine views at 1440, 1100 and 1024 px: no sideways scroll, no console errors, no request to another host, skip link first, every control reachable by keyboard. "
          + (f"Last run: {suites['e2e']['summary']}.\n\n" if suites else "Not run this time (pass --suites).\n\n")
          + f"Contrast (WCAG ratio from the CSS colours): lowest {a['min_contrast']}:1, target 4.5:1.\n\n"
          + table(list(a["ratios"].items()), ["Pair", "Ratio"]) + "\n\n"
          + "Chart label size (14 px at full width) as the page narrows: " + ", ".join(f"{k} {v} px" for k, v in a["chart_label_px_by_viewport"].items())
          + ". Computed from the SVG scale, not measured in a browser. Below 640 px the labels fall under 13 px.\n\n"
          + "Automated accessibility check (axe): not run, it could not be vendored offline.")
    text = put_section(text, "Browser tests", br)
    tc = (f"Unit and property: {ct['unit_and_property']} collected ({ct['property_tests']} of them property tests). End to end: {ct['end_to_end']}. Total {ct['total']}.\n"
          + (f"\nLast runs: unit and property, {suites['unit']['summary']} ({suites['unit']['seconds']} s). End to end, {suites['e2e']['summary']} ({suites['e2e']['seconds']} s)." if suites else ""))
    text = put_section(text, "Test counts", tc)
    text = put_section(text, "Not tested", "Real complaints, real handlers, many users at once beyond two, a live model under load, and a 100,000 case run in a browser. Spec section 26.")
    path.write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[1600, 16000, 160000])
    ap.add_argument("--suites", action="store_true", help="also run both test suites and record their results")
    a = ap.parse_args()
    d = {"machine": f"{platform.platform()}, {platform.processor() or platform.machine()}, Python {platform.python_version()}", "date": CFG["today"]}
    d["volume"], keep = volume(a.sizes)
    conn = sqlite3.connect(keep["path"])
    conn.row_factory = sqlite3.Row
    d["nine_views"] = nine_views(keep["client"])
    built, cls = classify_part(conn)
    d["stage_ms"] = stages(conn, built)
    d["accuracy"] = {"classifiers": cls, "retrieval": retrieval(conn), "drafts": draft_figures(conn)}
    d["security"] = {"masking": masking_set(), "injection": injection(conn), "headers": headers(keep["client"]), **security(conn)}
    d["ease_of_use"] = json.loads((ROOT / "docs/screenshots/flow-counts.json").read_text())
    d["accessibility"] = accessibility()
    d["test_counts"] = counts()
    d["odd_inputs"] = odd_rows()
    old = ROOT / "docs/bench.json"
    if not a.suites and old.exists():  # keep the last suite results when only the quick parts are re-run
        d["suites"] = json.loads(old.read_text()).get("suites")
    if a.suites:
        d["suites"] = {"unit": run_suite(["-q", "--ignore=tests/e2e"]), "e2e": run_suite(["tests/e2e", "-o", "addopts="])}
    (ROOT / "docs/bench.json").write_text(json.dumps(d, indent=1, default=str) + "\n", encoding="utf-8")
    write_docs(d)
    print(json.dumps({k: d[k] for k in ("volume", "nine_views")}, indent=1)[:1500])


if __name__ == "__main__":
    main()
