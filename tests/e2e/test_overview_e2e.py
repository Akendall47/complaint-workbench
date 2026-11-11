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

    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"

    # Tabs inside a panel work without script: the hour heatmap replaces the daily chart.
    assert page.locator(".area-chart").is_visible() and not page.locator(".heat-chart").is_visible()
    page.locator("label[for=trend-2]").click()
    assert page.locator(".heat-chart").is_visible() and not page.locator(".area-chart").is_visible()

    # Load more adds the next cases to the Needs attention list, in place.
    before = page.locator(".att li:not(.more-row)").count()
    if page.locator(".load-more").count():
        page.locator(".load-more").click()
        page.wait_for_function(f"document.querySelectorAll('.att li:not(.more-row)').length > {before}")
        assert page.url.rstrip("/") == base.rstrip("/")  # still on the Overview

    # Hovering a band in the complaint map names it; every band is a link to the Queue.
    assert page.locator(".map a").first.get_attribute("href").startswith("/queue?")

    if width == 1440:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.goto(base + "/")
        page.screenshot(path=str(SHOTS / "overview.png"))
    page.close()
