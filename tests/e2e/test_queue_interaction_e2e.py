"""Popover and role switch in a real browser. Uses the base and browser fixtures from test_queue_e2e."""
from tests.e2e.test_queue_e2e import base, browser  # noqa: F401  (fixtures)


def test_help_popover_and_role_switch(base, browser):  # noqa: F811
    page = browser.new_page(viewport={"width": 1440, "height": 768})
    page.goto(base + "/queue?owner=all&due=past")
    page.get_by_role("button", name="How this page works").click()
    assert page.locator("#help").is_visible()
    page.keyboard.press("Escape")
    assert not page.locator("#help").is_visible()
    assert page.evaluate("document.activeElement.getAttribute('data-open')") == "help"
    page.get_by_role("button", name="Team lead").click()
    page.wait_for_function("document.querySelector('[name=role][value=team_lead]').getAttribute('aria-pressed') === 'true'")
    assert page.url == base + "/queue?owner=all&due=past"
    page.close()
