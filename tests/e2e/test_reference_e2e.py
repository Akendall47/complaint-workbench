"""Browser pass on Policy library, Audit log and Settings. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

VIEWS = [("/policies", "policies"), ("/audit", "audit"), ("/settings", "settings")]


def team_lead(base, browser, **size):
    page = browser.new_page(**size)
    page.context.add_cookies([{"name": "role", "value": "team_lead", "url": base}, {"name": "staff_id", "value": "T1", "url": base}])
    return page


@pytest.mark.parametrize("width", [1440, 1100, 1024])
@pytest.mark.parametrize("path,name", VIEWS)
def test_reference_view_in_browser(base, browser, width, path, name):
    size = {"viewport": {"width": width, "height": 900}}
    page = team_lead(base, browser, **size) if name == "audit" else browser.new_page(**size)  # the log is for the team lead
    errors, hosts = [], set()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: hosts.add(r.url.split("/")[2]) if r.url.startswith("http") else None)
    page.goto(base + path)
    page.wait_for_load_state("networkidle")

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "sideways scroll"
    assert not errors, errors
    assert hosts <= {base.split("/")[2]}, hosts  # nothing is fetched from another site, the source links are only links

    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    want = len(set(page.locator("main a[href]:visible, main button:visible, main summary:visible, main input:visible, main select:visible, main textarea:visible")
                   .evaluate_all("els => els.map(e => e.outerHTML.slice(0, 160))")))  # identical links (a case listed twice) are one stop to check
    reached = set()
    for _ in range(300):
        page.keyboard.press("Tab")
        if page.evaluate("!!document.activeElement.closest('main')"):
            reached.add(page.evaluate("document.activeElement.outerHTML.slice(0, 160)"))
        if page.evaluate("document.activeElement === document.body"):
            break
    assert len(reached) >= want, (want, len(reached))
    page.close()


def test_settings_data_sources_link_lands_on_the_table(base, browser):
    page = browser.new_page(viewport={"width": 1024, "height": 700})
    page.goto(base + "/settings#data-sources")
    assert page.locator("#data-sources").is_visible() and page.locator("#data-sources table").is_visible()
    assert page.locator("#data-sources tbody tr").count() == 7
    assert page.locator("#data-sources a[target=_blank]").first.get_attribute("href").startswith("https://www.fca.org.uk/")
    assert "No real customer data is used." in page.locator("#data-sources").inner_text()
    page.close()


def test_policy_search_in_browser(base, browser):
    page = browser.new_page()
    page.goto(base + "/policies")
    page.get_by_label("Search the policy clauses").fill("executor")
    page.keyboard.press("Enter")
    page.wait_for_url("**/policies?q=executor")
    assert page.locator("mark").count() > 0
    page.close()


def test_policy_section_filter_and_clause_anchor_in_browser(base, browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto(base + "/policies")
    page.get_by_role("link", name="Bereavement").click()
    page.wait_for_url("**section=Bereavement")
    assert page.locator(".clause-list li[id]").count() == 5
    page.goto(base + "/policies#POL-8.5")  # the last clause: the anchor scrolls the panel, not the page
    assert page.evaluate("(() => { const r = document.getElementById('POL-8.5').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })()")
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
    page.close()


def test_audit_load_older_appends_rows_without_leaving_the_page(base, browser):
    page = team_lead(base, browser, viewport={"width": 1366, "height": 768})
    page.goto(base + "/audit")
    rows = page.locator("tbody tr:not(.more-row)")
    assert rows.count() == 50
    page.get_by_role("link", name="Load older").click()
    page.wait_for_function("document.querySelectorAll('tbody tr:not(.more-row)').length === 100")
    assert page.url.endswith("/audit")
    assert page.locator("text=Chain verified").is_visible()
    page.close()


def test_audit_view_as_team_lead_button_switches_role_and_stays(base, browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto(base + "/audit")
    assert page.locator("main table").count() == 0
    page.get_by_role("button", name="View as team lead").click()
    page.wait_for_selector("main table")
    assert page.url.endswith("/audit") and page.locator(".chain-chip").inner_text().startswith("Chain verified")
    page.close()
