"""Browser pass on the Queue. Run on its own: uv run pytest tests/e2e -o addopts="" (needs: uv run playwright install chromium)."""
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


@pytest.mark.parametrize("width", [1440, 1100, 1024])
def test_queue_in_browser(base, browser, width):
    page = browser.new_page(viewport={"width": width, "height": 768})
    errors, hosts = [], set()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: hosts.add(r.url.split("/")[2]) if r.url.startswith("http") else None)
    page.goto(base + "/queue?owner=all")
    page.wait_for_load_state("networkidle")

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "sideways scroll"
    assert not errors, errors
    assert hosts <= {base.split("/")[2]}, hosts

    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth")
    assert not outline.startswith("none") and not outline.endswith(" 0px"), outline
    page.evaluate("""window.ctl = [...document.querySelectorAll('a[href], button, summary, select, input:not([type=hidden])')]
        .filter(e => e.checkVisibility())""")
    wanted = page.evaluate("window.ctl.length")
    seen = set()
    for _ in range(wanted + 5):
        seen.add(page.evaluate("window.ctl.indexOf(document.activeElement)"))
        page.keyboard.press("Tab")
    seen.discard(-1)
    assert len(seen) == wanted, (len(seen), wanted)

    if width == 1440:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.goto(base + "/queue")
        page.screenshot(path=str(SHOTS / "queue.png"))
    page.close()
