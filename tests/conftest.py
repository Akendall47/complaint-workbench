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
