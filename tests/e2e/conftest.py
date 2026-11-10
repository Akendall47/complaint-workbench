"""Shared browser-test fixtures: a generated 1,600-case database served on a free port, and one Chromium."""
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

SHOTS = Path(__file__).resolve().parents[2] / "docs" / "screenshots"


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    from workbench.config import load_config
    from workbench.db import connect, init_db
    from workbench.generate import generate
    db = tmp_path_factory.mktemp("e2e") / "workbench.db"
    c = connect(db)
    init_db(c)
    cfg = load_config()
    generate(c, n=1600, seed=7, cfg=cfg)
    c.commit()
    from workbench.classify import apply_to_cases, build
    apply_to_cases(c, cfg, {k: v["model"] for k, v in build(c, cfg).items() if k in ("department", "type")})  # as the classify CLI does
    c.close()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    code = f"import uvicorn; from workbench.app import create_app; uvicorn.run(create_app(r'{db}', models_dir=None), host='127.0.0.1', port={port}, log_level='warning')"
    proc = subprocess.Popen([sys.executable, "-c", code])
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/static/app.css", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()
