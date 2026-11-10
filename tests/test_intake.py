import pytest

from workbench import audit
from workbench.db import connect, init_db
from workbench.generate import generate
from workbench.intake import IntakeError, receive


@pytest.fixture
def small(cfg):
    c = connect(":memory:")
    init_db(c)
    generate(c, n=60, seed=3, cfg=cfg)
    c.commit()
    yield c
    c.close()


@pytest.fixture
def models(built):
    return {"department": built["department"]["model"], "type": built["type"]["model"]}


TEXT = "My debit card was used abroad and it has never left my wallet. I want the payments investigated."


def test_receive_writes_everything(small, cfg, models):
    cid = receive(small, text=TEXT, source="phone", cfg=cfg, models=models)
    assert cid == "AB-2026-00061"
    r = small.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
    assert r["state"] == "new" and r["owner_id"] is None and r["received_at"] == "2026-11-10T12:30:00"
    assert r["department"] == "Fraud claims" and r["product_kind"] == "payment"
    assert r["deadline"] == "2026-12-01" and r["draft_state"] == "none"
    n = small.execute("SELECT body, seq FROM notes WHERE case_id=?", (cid,)).fetchone()
    assert (n["body"], n["seq"]) == (TEXT, 1)
    assert small.execute("SELECT kind FROM events WHERE case_id=?", (cid,)).fetchone()[0] == "received"
    assert small.execute("SELECT count(*) FROM audit WHERE case_id=?", (cid,)).fetchone()[0] == 1
    assert audit.verify_chain(small) is None


@pytest.mark.parametrize("bad", ["", "   \n"])
def test_empty(small, cfg, models, bad):
    with pytest.raises(IntakeError, match="Enter the complaint text."):
        receive(small, text=bad, source="phone", cfg=cfg, models=models)


def test_duplicate(small, cfg, models):
    a = receive(small, text=TEXT, source="phone", cfg=cfg, models=models)
    b = receive(small, text="  " + TEXT.upper().replace(" ", "  ") + " ", source="email", cfg=cfg, models=models)
    assert small.execute("SELECT duplicate_of FROM cases WHERE id=?", (b,)).fetchone()[0] == a
    assert small.execute("SELECT duplicate_of FROM cases WHERE id=?", (a,)).fetchone()[0] is None


def test_french_unrouted(small, cfg, models):
    cid = receive(small, text="Je voudrais faire une réclamation concernant les frais sur mon compte bancaire depuis des mois.",
                  source="letter", cfg=cfg, models=models)
    r = small.execute("SELECT department, draft_state FROM cases WHERE id=?", (cid,)).fetchone()
    assert r["department"] is None and r["draft_state"] == "none"


def test_bad_source(small, cfg, models):
    with pytest.raises(IntakeError):
        receive(small, text=TEXT, source="carrier pigeon", cfg=cfg, models=models)


def test_too_long(small, cfg, models):
    with pytest.raises(IntakeError, match="Complaint text is too long. The limit is 5,000 characters."):
        receive(small, text="word " * 1001, source="phone", cfg=cfg, models=models)
    receive(small, text=("word " * 999).strip(), source="phone", cfg=cfg, models=models)
