"""Department and complaint-type classifiers. Trained on note 1 only: the customer's own words."""
import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from workbench.config import load_config
from workbench.db import connect
from workbench.urgency import is_urgent, urgent_reasons

MODELS_DIR = Path("data/models")
_COMMON = frozenset((Path(__file__).parent / "common_words.txt").read_text(encoding="utf-8").split())


class Prediction(NamedTuple):
    label: str
    confidence: float
    top_words: list[str]


def train(texts: list[str], labels: list[str]) -> Pipeline:
    m = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                  ("clf", LogisticRegression(max_iter=1000))])
    return m.fit(texts, labels)


def predict(model: Pipeline, text: str) -> Prediction:
    vec, clf = model["tfidf"], model["clf"]
    x = vec.transform([text])
    proba = clf.predict_proba(x)[0]
    i = int(proba.argmax())
    coef = clf.coef_[i] if len(clf.classes_) > 2 else clf.coef_[0] * (1 if i == 1 else -1)
    cols = x.indices[coef[x.indices] > 0]  # features that occur in the text and push toward this class
    cols = cols[np.argsort(-coef[cols])][:5]
    names = getattr(vec, "_names", None)
    if names is None:  # building this array costs about 10 ms, so do it once per model
        names = vec._names = vec.get_feature_names_out()
    return Prediction(str(clf.classes_[i]), float(proba[i]), [str(names[c]) for c in cols])


def looks_english(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.casefold())
    if len(words) < 5:
        return True
    return sum(w in _COMMON for w in words) / len(words) >= 0.3


@lru_cache(maxsize=None)
# Safe: loads only the models this repo builds into data/models/ (committed build output), never user-supplied files.
def load_models(models_dir: str = str(MODELS_DIR)) -> dict:
    return {k: joblib.load(Path(models_dir) / f"{k}.joblib") for k in ("department", "type")}


def _note1(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.id, c.department_true, c.type_true, n.body FROM cases c JOIN notes n ON n.case_id = c.id"
        " WHERE n.seq = (SELECT MIN(seq) FROM notes WHERE case_id = c.id) ORDER BY c.id").fetchall()


def _evaluate(model, texts, truth, threshold) -> dict:
    proba = model.predict_proba(texts)
    classes = list(model.classes_)
    pred = [classes[i] for i in proba.argmax(1)]
    conf = proba.max(1)
    ok = np.array([p == t for p, t in zip(pred, truth)])
    sure = conf >= threshold
    per = {}
    for c in sorted(set(truth) | set(pred)):
        tp = sum(p == c and t == c for p, t in zip(pred, truth))
        npred, ntrue = pred.count(c), truth.count(c)
        per[c] = {"n": ntrue, "precision": tp / npred if npred else 0.0, "recall": tp / ntrue if ntrue else 0.0}
    return {"accuracy": float(ok.mean()), "per_class": per, "n_test": len(truth),
            "confusion": Counter((t, p) for p, t in zip(pred, truth)),
            "below_share": float(1 - sure.mean()),
            "accuracy_above": float(ok[sure].mean()) if sure.any() else float("nan")}


def build(conn: sqlite3.Connection, cfg: dict) -> dict:
    """Train both models on 80% of cases (split seed 7), score them on the other 20%."""
    rows = _note1(conn)
    idx_tr, idx_te = train_test_split(range(len(rows)), test_size=0.2, random_state=7)
    out = {}
    for key, col in (("department", "department_true"), ("type", "type_true")):
        get = lambda ix: ([rows[i]["body"] for i in ix], [rows[i][col] for i in ix])  # noqa: E731
        model = train(*get(idx_tr))
        out[key] = {"model": model, **_evaluate(model, *get(idx_te), cfg["routing_threshold"])}
    return out


def apply_to_cases(conn: sqlite3.Connection, cfg: dict, models: dict) -> dict:
    """Write predictions, routing and urgency for every case. Returns urgency reason counts."""
    rows = _note1(conn)
    texts = [r["body"] for r in rows]
    thr, today = cfg["routing_threshold"], date.fromisoformat(cfg["today"])
    res = {}
    for key in ("department", "type"):
        proba = models[key].predict_proba(texts)
        res[key] = ([str(models[key].classes_[i]) for i in proba.argmax(1)], proba.max(1))
    for r, dep, dc, ty, tc, ok in zip(rows, *res["department"], *res["type"], map(looks_english, texts)):
        routed = dep if (dc >= thr and ok) else None  # below threshold or not English: "Needs routing"
        conn.execute("UPDATE cases SET department_pred=?, department_conf=?, department=?, type=?, type_conf=? WHERE id=?",
                     (dep, float(dc), routed, ty, float(tc), r["id"]))
    notes = {}
    for r in conn.execute("SELECT case_id, body FROM notes ORDER BY case_id, seq"):
        notes.setdefault(r["case_id"], []).append(r["body"])
    counts = Counter()
    for c in conn.execute("SELECT id, state, deadline, return_count, urgent_manual FROM cases").fetchall():
        text = "\n".join(notes.get(c["id"], []))
        reasons = urgent_reasons(c, text, today, cfg)
        counts.update(reasons)
        counts["urgent"] += is_urgent(c, text, today, cfg)
        conn.execute("UPDATE cases SET urgent=? WHERE id=?", (int(is_urgent(c, text, today, cfg)), c["id"]))
    conn.commit()
    return dict(counts)


def _table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def _section(title, res, thr) -> str:
    per = [(c, v["n"], f"{v['precision']:.2f}", f"{v['recall']:.2f}") for c, v in res["per_class"].items()]
    classes = list(res["per_class"])
    conf = [[t] + [res["confusion"][(t, p)] for p in classes] for t in classes]
    pairs = [(t, p, n) for (t, p), n in res["confusion"].most_common() if t != p][:3]
    return "\n\n".join([
        f"### {title}",
        f"Accuracy on the held-out 20% ({res['n_test']} cases): **{res['accuracy']:.3f}**.",
        f"Cases below the routing threshold ({thr}): {res['below_share']:.1%}. "
        f"Accuracy counting only predictions at or above it: {res['accuracy_above']:.3f}.",
        _table(["Class", "Test cases", "Precision", "Recall"], per),
        "Confusion table (rows are the true class, columns the predicted class):",
        _table(["True \\ predicted"] + classes, conf),
        "Most confused pairs: " + "; ".join(f"{t} read as {p} ({n})" for t, p, n in pairs) + ".",
    ])


def write_report(built: dict, cfg: dict, path: Path) -> None:
    thr = cfg["routing_threshold"]
    body = "\n\n".join([
        "## Classifiers",
        "Both models read note 1 only, the customer's own words, because routing happens before staff notes exist. "
        "Labels are the generator's `department_true` and `type_true`. Split: 80/20, seed 7. "
        "Figures come from `uv run python -m workbench.classify`; the generated labels carry deliberate noise, so these are not real-world figures.",
        _section("Department routing", built["department"], thr),
        _section("Complaint type", built["type"], thr),
    ]) + "\n"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Test results\n"
    text = re.sub(r"\n?## Classifiers\n.*?(?=\n## |\Z)", "", text, flags=re.S).rstrip("\n")
    path.write_text(text + "\n\n" + body, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Train the classifiers, write predictions and urgency for every case.")
    ap.add_argument("--db", default="data/workbench.db")
    ap.add_argument("--config", default="config/pipeline.yaml")
    ap.add_argument("--models-dir", default=str(MODELS_DIR))
    ap.add_argument("--report", default="docs/test-results.md")
    a = ap.parse_args()
    cfg = load_config(a.config)
    conn = connect(a.db)
    built = build(conn, cfg)
    Path(a.models_dir).mkdir(parents=True, exist_ok=True)
    for k in ("department", "type"):
        joblib.dump(built[k]["model"], Path(a.models_dir) / f"{k}.joblib")
    write_report(built, cfg, Path(a.report))
    counts = apply_to_cases(conn, cfg, {k: built[k]["model"] for k in ("department", "type")})
    conn.close()
    print(json.dumps({"department_accuracy": built["department"]["accuracy"], "type_accuracy": built["type"]["accuracy"],
                      "urgent": counts}, indent=1))


if __name__ == "__main__":
    main()
