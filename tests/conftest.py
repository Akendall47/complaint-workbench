import time

import pytest

from workbench.config import load_config
from workbench.db import connect, init_db
from workbench.generate import generate


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def p(cfg):
    return cfg["masking"]


@pytest.fixture(scope="session")
def db_timed():
    """The 1,600-row generated database, built once, with its build time in seconds."""
    t0 = time.perf_counter()
    c = connect(":memory:")
    init_db(c)
    generate(c, n=1600, seed=7, cfg=load_config())
    c.commit()
    secs = time.perf_counter() - t0
    yield c, secs
    c.close()


@pytest.fixture(scope="session")
def db(db_timed):
    return db_timed[0]


@pytest.fixture(scope="session")
def built(db):
    """Models trained once on the shared generated database (80% split, seed 7)."""
    from workbench.classify import build
    return build(db, load_config())


@pytest.fixture(scope="session")
def app_db_file(tmp_path_factory):
    """A small generated database on disk (200 cases) for web tests. Copy it before changing anything."""
    path = tmp_path_factory.mktemp("appdb") / "workbench.db"
    c = connect(path)
    init_db(c)
    generate(c, n=200, seed=7, cfg=load_config())
    c.commit()
    c.close()
    return path


@pytest.fixture
def app_db(app_db_file, tmp_path):
    """A private copy of the 200-case database, so a test may change it."""
    import shutil
    from workbench import audit
    dst = tmp_path / "workbench.db"
    shutil.copy(app_db_file, dst)
    yield dst
    audit.set_clock(None)  # create_app pins the demo clock


@pytest.fixture
def client(app_db):
    from fastapi.testclient import TestClient
    from workbench.app import create_app
    return TestClient(create_app(str(app_db), models_dir=None), base_url="http://127.0.0.1:8000",
                      headers={"Origin": "http://127.0.0.1:8000"})
