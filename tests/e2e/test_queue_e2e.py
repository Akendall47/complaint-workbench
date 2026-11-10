"""Browser pass on the Queue. Run on its own: uv run pytest tests/e2e -o addopts="" (needs: uv run playwright install chromium)."""
import pytest

from tests.e2e.conftest import SHOTS


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
