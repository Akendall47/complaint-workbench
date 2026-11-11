"""Retake the screenshots in docs/screenshots: every page at 1366 x 768, as the role that uses it most.
Works on a copy of data/workbench.db, so the shipped database is not changed. Run: uv run python docs/screenshots/take.py"""
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
ROLES = {"handler": "H1", "specialist": "S1", "team_lead": "T1"}
SHOTS = [("overview", "/", "team_lead"), ("queue", "/queue", "handler"), ("case", "/cases/AB-2026-00768", "handler"),
         ("case-specialist", "/cases/AB-2026-00768", "specialist"), ("departments", "/departments", "specialist"),
         ("team", "/team", "team_lead"), ("pipeline", "/pipeline", "team_lead"), ("policies", "/policies", "handler"),
         ("audit", "/audit", "team_lead"), ("settings", "/settings", "team_lead")]

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "workbench.db"
    shutil.copy(ROOT / "data" / "workbench.db", db)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    code = f"import uvicorn; from workbench.app import create_app; uvicorn.run(create_app(r'{db}'), host='127.0.0.1', port={port}, log_level='warning')"
    server = subprocess.Popen([sys.executable, "-c", code], cwd=ROOT)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(150):  # the first start may train the two small models
            try:
                urllib.request.urlopen(url + "/static/app.css", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, path, role in SHOTS:
                ctx = browser.new_context(viewport={"width": 1366, "height": 768})
                ctx.add_cookies([{"name": "role", "value": role, "url": url}, {"name": "staff_id", "value": ROLES[role], "url": url}])
                page = ctx.new_page()
                page.goto(url + path)
                page.wait_for_load_state("networkidle")
                page.screenshot(path=str(OUT / f"{name}.png"))
                ctx.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()
print(f"wrote {len(SHOTS)} screenshots to {OUT}")
