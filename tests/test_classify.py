import json
from pathlib import Path

import time

from workbench.classify import looks_english, predict, train


def test_department_accuracy(built):
    assert built["department"]["accuracy"] >= 0.81


def test_type_accuracy(built):
    assert built["type"]["accuracy"] >= 0.96


def test_predict_shape(built):
    pr = predict(built["department"]["model"], "Someone made payments on my card that I did not make and I think it is a scam.")
    assert pr.label == "Fraud claims" and 0 < pr.confidence <= 1
    assert 0 < len(pr.top_words) <= 5


def test_top_words_present_in_text(built):
    text = "my father died and I am the executor of the estate"
    pr = predict(built["department"]["model"], text)
    assert pr.top_words and all(w.split()[0] in text for w in pr.top_words)


def test_even_mix_is_below_threshold(built, cfg):
    t = ("Someone made payments on my card that I did not make. "
         "My father died last month and I am dealing with the estate.")
    pr = predict(built["department"]["model"], t)
    assert pr.confidence < cfg["routing_threshold"], pr


def test_nonsense_type_is_other_or_unsure(built):
    pr = predict(built["type"]["model"], "zzyzx plugh quux frobnicate")
    assert pr.label == "Other" or pr.confidence < 0.45


def test_predict_is_fast(built):
    m = built["department"]["model"]
    t0 = time.perf_counter()
    for _ in range(50):
        predict(m, "I was charged an overdraft fee that I was never told about.")
    assert (time.perf_counter() - t0) / 50 < 0.02


def test_train_returns_pipeline():
    m = train(["red apple", "blue sky", "red rose", "blue sea"], ["x", "y", "x", "y"])
    assert predict(m, "red").label == "x"


def test_looks_english():
    assert looks_english("I want to make a complaint about the charge on my account.")
    assert not looks_english("Je voudrais faire une réclamation concernant les frais sur mon compte bancaire.")
    assert looks_english("Help me")  # under 5 words skips the check


def _norm(t):
    import re
    return " ".join(re.sub(r"[\d\W_]+", " ", t.lower()).split())


def test_no_text_shared_between_train_and_test(built, db):
    train_ids, test_ids = built["split"]
    body = {r["case_id"]: r["body"] for r in db.execute("SELECT case_id, body FROM notes WHERE seq = 1")}
    seen = {_norm(body[i]) for i in train_ids}
    assert not any(_norm(body[i]) in seen for i in test_ids)
    assert built["old_split_overlap"] >= 0


def test_ensure_models_trains_when_missing(db, cfg, tmp_path):
    from workbench.classify import ensure_models
    d = tmp_path / "models"
    m = ensure_models(db, cfg, d)
    assert (d / "department.joblib").exists() and (d / "type.joblib").exists()
    assert predict(m["department"], "my card was used by a fraudster").label
    assert ensure_models(db, cfg, d)["type"] is not None  # second call loads


def test_cli_rerun_is_stable(db, tmp_path, monkeypatch):
    import sqlite3
    import sys

    from workbench.classify import main
    path = tmp_path / "w.db"
    dst = sqlite3.connect(path)
    db.backup(dst)
    dst.close()
    report = tmp_path / "r.md"
    report.write_text("# Test results\n\n## Keep me\nhello\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["classify", "--db", str(path), "--models-dir", str(tmp_path / "m"), "--report", str(report)])
    main()
    first = report.read_text(encoding="utf-8")
    main()
    assert report.read_text(encoding="utf-8") == first
    assert "## Keep me\nhello" in first and first.count("## Classifiers") == 1
    c = sqlite3.connect(path)
    fid = json.loads((Path(__file__).parent / "adversarial_ids.json").read_text())["french"]
    assert c.execute("SELECT department FROM cases WHERE id=?", (fid,)).fetchone()[0] is None
    c.close()
