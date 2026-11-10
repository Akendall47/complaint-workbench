"""Browser pass on the Overview. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

from tests.e2e.conftest import SHOTS


@pytest.mark.parametrize("width", [1440, 1100, 1024])
def test_overview_in_browser(base, browser, width):
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors, hosts = [], set()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: hosts.add(r.url.split("/")[2]) if r.url.startswith("http") else None)
    page.goto(base + "/")
    page.wait_for_load_state("networkidle")

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "sideways scroll"
    assert not errors, errors
    assert hosts <= {base.split("/")[2]}, hosts
    if width == 1440:  # the whole page fits: the foot link is inside the viewport
        assert page.evaluate("document.querySelector('.source a').getBoundingClientRect().bottom <= window.innerHeight")

    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"

    # Keyboard reach: Tab through the page until the chart's details summary has focus, passing all five case links.
    seen = set()
    for _ in range(60):
        page.keyboard.press("Tab")
        href = page.evaluate("document.activeElement.getAttribute('href') || ''")
        if href.startswith("/cases/"):
            seen.add(href)
        if page.evaluate("document.activeElement.matches('.chart-data summary')"):
            break
    else:
        pytest.fail("chart details not reachable by keyboard")
    assert len(seen) == 5, seen
    page.keyboard.press("Enter")
    assert page.locator(".chart-data table").is_visible()
    assert page.locator("main svg a, main svg [tabindex]").count() == 0  # the drawing is not a tab stop

    if width == 1440:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.goto(base + "/")
        page.screenshot(path=str(SHOTS / "overview.png"))
    page.close()
