"""Browser pass on Departments, Team and Pipeline. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

from tests.e2e.conftest import SHOTS

VIEWS = [("/departments", "departments"), ("/team", "team"), ("/pipeline", "pipeline")]


@pytest.mark.parametrize("width", [1440, 1100, 1024])
@pytest.mark.parametrize("path,name", VIEWS)
def test_work_view_in_browser(base, browser, width, path, name):
    page = browser.new_page(viewport={"width": width, "height": 900})
    if name == "team":  # the screenshot shows the whole team
        page.context.add_cookies([{"name": "role", "value": "team_lead", "url": base}, {"name": "staff_id", "value": "T1", "url": base}])
    errors, hosts = [], set()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: hosts.add(r.url.split("/")[2]) if r.url.startswith("http") else None)
    page.goto(base + path)
    page.wait_for_load_state("networkidle")

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "sideways scroll"
    assert not errors, errors
    assert hosts <= {base.split("/")[2]}, hosts

    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    # Every link, button and summary in the main area can take keyboard focus in turn.
    want = page.locator("main a[href]:visible, main button:visible, main summary:visible").count()
    reached = set()
    for _ in range(200):
        page.keyboard.press("Tab")
        if page.evaluate("!!document.activeElement.closest('main')"):
            reached.add(page.evaluate("document.activeElement.outerHTML.slice(0, 120)"))
        if page.evaluate("document.activeElement === document.body"):
            break
    assert len(reached) >= want, (want, len(reached))
    assert page.locator("main svg a, main svg [tabindex]").count() == (page.locator("main svg a").count() if name == "pipeline" else 0)

    if width == 1440:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.goto(base + path)
        page.screenshot(path=str(SHOTS / f"{name}.png"))
    page.close()
