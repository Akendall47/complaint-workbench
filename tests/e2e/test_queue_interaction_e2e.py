"""Queue in a real browser: help popover, role switch, and working the list (select a row, Next case, arrow keys, Load more, filters)."""
def test_help_popover_and_role_switch(base, browser):
    page = browser.new_page(viewport={"width": 1440, "height": 768})
    page.goto(base + "/queue?owner=all&due=past")
    page.get_by_role("button", name="Help").click()
    assert page.locator("#help").is_visible()
    page.keyboard.press("Escape")
    assert not page.locator("#help").is_visible()
    assert page.evaluate("document.activeElement.getAttribute('data-open')") == "help"
    page.get_by_role("button", name="Team lead").click()
    page.wait_for_function("document.querySelector('[name=role][value=team_lead]').getAttribute('aria-pressed') === 'true'")
    assert page.url == base + "/queue?owner=all&due=past"
    page.close()


def test_work_the_list_without_leaving_the_page(base, browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base + "/queue?owner=all")
    rows = page.locator("tr.case-row")
    ids = [rows.nth(i).get_attribute("data-case") for i in range(4)]
    shown = lambda: page.locator("#preview .pv-id").inner_text()  # noqa: E731
    checked = lambda: page.evaluate("document.querySelector('.q-pick:checked').closest('tr').dataset.case")  # noqa: E731
    assert shown() == ids[0] == checked()

    with page.expect_response(lambda r: f"/queue/preview/{ids[2]}" in r.url):
        rows.nth(2).locator(".q-hit").click()  # the label covers the row
    page.wait_for_function(f"document.querySelector('#preview .pv-id').textContent === '{ids[2]}'")
    assert checked() == ids[2]

    with page.expect_response(lambda r: f"/queue/preview/{ids[3]}" in r.url):
        page.get_by_role("link", name="Next case").click()
    page.wait_for_function(f"document.querySelector('#preview .pv-id').textContent === '{ids[3]}'")
    assert checked() == ids[3]  # the row selection followed

    page.locator(".q-pick:checked").focus()
    with page.expect_response(lambda r: "/queue/preview/" in r.url):
        page.keyboard.press("ArrowUp")
    page.wait_for_function(f"document.querySelector('#preview .pv-id').textContent === '{ids[2]}'")
    assert page.evaluate("document.activeElement.name") == "pick"  # focus stays on the list

    with page.expect_response(lambda r: "/queue/more" in r.url):
        page.locator(".load-more").click()
    page.wait_for_function("document.querySelectorAll('tr.case-row').length === 100")
    assert page.locator("#shown").inner_text().startswith("Showing 100 of")

    with page.expect_response(lambda r: "department=Fraud" in r.url):
        page.select_option("select[name=department]", "Fraud claims")
    page.wait_for_function("document.querySelectorAll('tr.case-row').length <= 50")
    assert "department=Fraud" in page.url and page.get_by_role("link", name="Clear filters").is_visible()
    assert page.locator("#preview .pv-id").inner_text() == rows.first.get_attribute("data-case")
    assert not errors, errors
    page.close()
