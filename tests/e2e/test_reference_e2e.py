"""Browser pass on Policy library, Audit log and Settings. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

from tests.e2e.conftest import SHOTS

VIEWS = [("/policies", "policies"), ("/audit", "audit"), ("/settings", "settings")]


@pytest.mark.parametrize("width", [1440, 1100, 1024])
@pytest.mark.parametrize("path,name", VIEWS)
def test_reference_view_in_browser(base, browser, width, path, name):
    page = browser.new_page(viewport={"width": width, "height": 900})
    if name == "audit":  # the log is for the Team lead
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
    want = page.locator("main a[href]:visible, main button:visible, main summary:visible, main input:visible, main select:visible, main textarea:visible").count()
    reached = set()
    for _ in range(300):
        page.keyboard.press("Tab")
        if page.evaluate("!!document.activeElement.closest('main')"):
            reached.add(page.evaluate("document.activeElement.outerHTML.slice(0, 160)"))
        if page.evaluate("document.activeElement === document.body"):
            break
    assert len(reached) >= want, (want, len(reached))

    if width == 1440:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.goto(base + path)
        page.screenshot(path=str(SHOTS / f"{name}.png"))
    page.close()


def test_settings_data_sources_link_lands_on_the_table(base, browser):
    page = browser.new_page(viewport={"width": 1024, "height": 700})
    page.goto(base + "/settings#data-sources")
    assert page.locator("#data-sources").is_visible() and page.locator("#data-sources ~ .table-wrap table").is_visible()
    page.close()


def test_policy_search_in_browser(base, browser):
    page = browser.new_page()
    page.goto(base + "/policies")
    page.get_by_label("Search the policy clauses").fill("executor")
    page.keyboard.press("Enter")
    page.wait_for_url("**/policies?q=executor")
    assert page.locator("mark").count() > 0
    page.close()
