import pytest

from workbench.config import load_config
from workbench.db import connect, init_db


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def cfg():
    return load_config()
