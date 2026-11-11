"""Browser pass on Departments, Team and Pipeline. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

VIEWS = [("/departments", "departments"), ("/team", "team"), ("/pipeline", "pipeline")]


@pytest.mark.parametrize("width", [1440, 1100, 1024])
@pytest.mark.parametrize("path,name", VIEWS)
def test_work_view_in_browser(base, browser, width, path, name):
    page = browser.new_page(viewport={"width": width, "height": 900})
    if name == "team":  # the whole team
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
    for _ in range(300):
        page.keyboard.press("Tab")
        if page.evaluate("!!document.activeElement.closest('main')"):
            reached.add(page.evaluate("document.activeElement.outerHTML.slice(0, 120)"))
        if page.evaluate("document.activeElement === document.body"):
            break
    assert len(reached) >= want, (want, len(reached))
    if name == "pipeline":  # in the flow only stage links and unlinked bands take focus
        assert page.locator("main svg [tabindex]:not(.band)").count() == 0 and page.locator("main svg a [tabindex]").count() == 0
    else:
        assert page.locator("main svg a, main svg [tabindex]").count() == 0
    page.close()


def test_specialist_accepts_a_waiting_case(base, browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.context.add_cookies([{"name": "role", "value": "specialist", "url": base}, {"name": "staff_id", "value": "S1", "url": base}])
    page.goto(base + "/departments")
    first = page.locator(".waiting tbody tr").first
    cid = first.locator(".plain-id").inner_text()
    first.get_by_role("button", name="Accept").click()
    page.wait_for_url(f"**/cases/{cid}**")
    assert "Accepted" in page.locator("main").inner_text()
    page.close()


def test_load_more_appends_handovers_in_place(base, browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.context.add_cookies([{"name": "role", "value": "team_lead", "url": base}, {"name": "staff_id", "value": "T1", "url": base}])
    page.goto(base + "/departments")
    rows = page.locator(".waiting tbody tr:not(.more-tr)")
    assert rows.count() == 20
    page.locator(".waiting .load-more").click()
    page.wait_for_function("document.querySelectorAll('.waiting tbody tr:not(.more-tr)').length > 20")
    assert page.url.endswith("/departments") and page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
    page.close()


def test_clicking_a_stage_leaves_no_box_and_opens_the_queue(base, browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto(base + "/pipeline")
    link = page.locator(".flow a").first
    link.focus()
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") == "none"
    page.locator(".flow a .flow-stage").first.click()
    page.wait_for_url("**/queue?owner=all&state=new")
    page.close()
