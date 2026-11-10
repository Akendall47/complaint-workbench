import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from tests.test_generate import CFG, fresh, db  # noqa: F401  (db is the session fixture)


def test_ownership_without_specialist(db):
    t1 = db.execute("SELECT COUNT(*) FROM cases WHERE owner_id='T1' AND state != 'accepted'").fetchone()[0]
    assert t1 < 40
    assert db.execute("SELECT COUNT(*) FROM cases WHERE owner_id='T1' AND return_count < 2").fetchone()[0] == 0
    bad = db.execute("""SELECT COUNT(*) FROM cases WHERE state IN ('handed_over','accepted') AND return_count < 2
        AND department_true IN ('Bereavement','Mis-selling review','General service') AND owner_id NOT LIKE 'H%'""").fetchone()[0]
    assert bad == 0
    load = Counter({r[0]: r[1] for r in db.execute(
        "SELECT owner_id, COUNT(*) FROM cases WHERE state != 'accepted' AND owner_id LIKE 'H%' GROUP BY 1")})
    assert load.most_common(1)[0][0] == "H3"
    assert db.execute("SELECT COUNT(*) FROM cases WHERE owner_id='H1' AND state IN ('new','in_review','returned')").fetchone()[0] >= 25


def test_type_noise(db):
    from workbench.generate import TYPE_C
    n = 0
    for r in db.execute("""SELECT c.type_true t, n.body b FROM cases c JOIN notes n ON n.case_id=c.id AND n.seq=1
                           WHERE LENGTH(n.body) < 5000"""):
        n += any(s in r["b"] for k, v in TYPE_C.items() if k != r["t"] for s in v)
    assert 0.07 <= n / 1600 <= 0.13


def test_field_labels_varied_and_no_department_names(db):
    from workbench.generate import FIELD
    assert all(len(v[0]) >= 3 for v in FIELD.values())
    body = " ".join(r[0] for r in db.execute("SELECT body FROM notes WHERE LENGTH(body) < 5000")).lower()
    for w in ("bereavement", "mis-sold", "mis-selling", "fraud claims", "financial difficulty", "data protection", "general service"):
        assert w not in body, w


def test_truth_matches_text(db):
    terms = CFG["urgent"]["vulnerability_terms"] + CFG["urgent"]["hardship_terms"]
    n = 0
    for r in db.execute("""SELECT c.handover_true_json h, group_concat(n.body, ' ') b FROM cases c JOIN notes n ON n.case_id=c.id
                           WHERE c.department_true='Financial difficulty' GROUP BY c.id"""):
        flagged = any(t in r["b"].lower() for t in terms)
        assert (not json.loads(r["h"])["vulnerability_noted"].startswith("none")) == flagged
        n += flagged
    assert n > 0
    for r in db.execute("""SELECT c.handover_true_json h, n.body b FROM cases c JOIN notes n ON n.case_id=c.id AND n.seq=1
                           WHERE c.department_true='Bereavement'"""):
        assert json.loads(r["h"])["relationship_to_deceased"] in r["b"]


def test_cli_adversarial_file_rule(tmp_path, monkeypatch):
    from workbench import generate as g
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    cfg = Path(__file__).parent.parent / "config" / "pipeline.yaml"
    monkeypatch.setattr(sys, "argv", ["g", "--n", "300", "--db", str(tmp_path / "a.db"), "--config", str(cfg)])
    g.main()
    assert not (tmp_path / "tests" / "adversarial_ids.json").exists()


PINNED = "7542a7121ae5916ba5ab766baf2ae8cc39094244a7e4232fcfff8c2cd1ba8a68"


def test_pinned_digest_n300():
    c = fresh(300, 7)
    h = hashlib.sha256()
    for r in c.execute("SELECT id FROM cases ORDER BY id"):
        h.update(r[0].encode())
    for r in c.execute("SELECT body FROM notes ORDER BY id"):
        h.update(r[0].encode())
    assert h.hexdigest() == PINNED


def test_unowned_authors_and_note_times(db):
    assert db.execute("""SELECT COUNT(*) FROM notes n JOIN cases c ON c.id=n.case_id
                         WHERE c.owner_id IS NULL AND n.seq > 1 AND n.author = 'T1'""").fetchone()[0] == 0
    assert db.execute("""SELECT COUNT(*) FROM notes n JOIN cases c ON c.id=n.case_id
                         WHERE n.written_at < c.received_at OR n.written_at > '2026-11-10T13:00:00'""").fetchone()[0] == 0
