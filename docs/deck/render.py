"""Render the five-slide deck to docs/deck.pdf and one PNG per slide. Run from the repo root: uv run python docs/deck/render.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto((HERE / "deck.html").resolve().as_uri())
    page.wait_for_load_state("networkidle")
    page.pdf(path=str(HERE.parent / "deck.pdf"), width="1920px", height="1080px", print_background=True)
    for i, slide in enumerate(page.query_selector_all(".slide"), 1):
        slide.screenshot(path=str(HERE / f"slide-{i}.png"))
    browser.close()
print("wrote docs/deck.pdf and docs/deck/slide-1.png to slide-5.png")
