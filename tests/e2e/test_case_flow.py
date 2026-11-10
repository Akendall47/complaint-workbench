"""Case view in a real browser: the full flow, the ui-notes checks at three widths, clicks and keystrokes counted.
Run: uv run pytest tests/e2e -o addopts="" """
import json
import sqlite3
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import SHOTS

REC = Path(__file__).resolve().parents[2] / "data" / "recordings"


def candidates(db):
    """Open Fraud claims cases of H1 in review, with a recording, in Queue order."""
    c = sqlite3.connect(db)
    try:
        rows = c.execute("SELECT id FROM cases WHERE owner_id='H1' AND state='in_review' AND department='Fraud claims' AND return_count=0 "
                         "ORDER BY deadline, urgent DESC, id").fetchall()
    finally:
        c.close()
    return [r[0] for r in rows if (REC / f"{r[0]}.json").exists()]


def db_value(db, q, *a):
    c = sqlite3.connect(db)
    try:
        return c.execute(q, a).fetchone()[0]
    finally:
        c.close()


class Count:
    """Clicks and keystrokes made by the person (typed characters count one each)."""
    def __init__(self, page):
        self.page, self.clicks, self.keys = page, 0, 0

    def click(self, loc):
        if loc.evaluate("e => e.tagName === 'BUTTON' && e.type === 'submit' && !!e.form.getAttribute('hx-post')"):
            with self.page.expect_response(lambda r: r.request.method == "POST"):
                loc.click()
            self.page.wait_for_timeout(250)  # the swap
        else:
            loc.click()
        self.clicks += 1

    def press(self, key):
        self.page.keyboard.press(key)
        self.keys += 1

    def fill(self, loc, text):
        loc.fill(text)
        self.keys += len(text)

    def confirm_by_keyboard(self):
        """Tab to the next Confirm button and press Enter, as a keyboard user would."""
        for _ in range(80):
            if self.page.evaluate("document.activeElement.classList.contains('confirm')"):
                before = self.page.locator("#live").inner_text()
                with self.page.expect_response(lambda r: r.request.method == "POST"):
                    self.press("Enter")
                self.page.wait_for_timeout(250)
                inside = self.page.evaluate("!!document.activeElement.closest('#case') && document.activeElement.tagName !== 'DIV'")
                assert inside, "focus fell out of the case after a swap"
                if self.page.locator("button.confirm").count():
                    assert self.page.evaluate("document.activeElement.classList.contains('confirm')")
                assert self.page.locator("#live").inner_text() != before, "no announcement after the swap"
                return True
            self.press("Tab")
        return False


def new_page(browser, base, width=1440):
    page = browser.new_page(viewport={"width": width, "height": 900})
    page.errors, page.hosts = [], set()
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on("request", lambda r: page.hosts.add(r.url.split("/")[2]) if r.url.startswith("http") else None)
    return page


def switch(page, name):
    page.get_by_role("button", name=name, exact=True).click()
    page.locator(f".role-switch button[aria-pressed=true]", has_text=name).wait_for()
    page.wait_for_load_state("networkidle")


def test_screenshots_from_a_fresh_database(base, dbfile, browser):
    """Run first in this module: viewport-size shots before the flow writes anything."""
    from workbench import drafts
    from workbench.config import load_config
    from workbench.db import connect
    SHOTS.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    mid, handed = candidates(dbfile)[3], candidates(dbfile)[4]
    c = connect(dbfile)  # the second case is handed over the way a handler would leave it: claims confirmed, handover saved
    c.execute("UPDATE claims SET status='confirmed' WHERE case_id=? AND supported=1", (handed,))
    c.execute("UPDATE claims SET status='removed' WHERE case_id=? AND status='draft'", (handed,))
    pack = drafts.load_handover(c, handed, cfg)
    c.execute("UPDATE cases SET state='handed_over', handover_json=?, owner_id='S1' WHERE id=?", (json.dumps(pack), handed))
    c.commit()
    c.close()
    page = new_page(browser, base)
    page.goto(f"{base}/cases/{mid}")
    page.locator("button.confirm").first.click()
    expect(page.locator(".stepper a").first).to_contain_text("1 of")
    page.screenshot(path=str(SHOTS / "case.png"))
    switch(page, "Specialist")
    page.goto(f"{base}/cases/{handed}")
    page.screenshot(path=str(SHOTS / "case-specialist.png"))
    page.close()


def test_full_flow(base, dbfile, browser):
    cid = candidates(dbfile)[0]
    page = new_page(browser, base)
    n = Count(page)
    from workbench.config import load_config
    assert cid == load_config()["demo_case"]
    page.goto(base + "/queue?owner=me&state=in_review&department=Fraud+claims")  # a filtered Queue (the URL stands in for the Filters form)
    first = page.locator("tr.case-row a").first
    assert first.get_attribute("href") == f"/cases/{cid}"
    n.click(first)
    page.wait_for_load_state("networkidle")
    assert page.url == f"{base}/cases/{cid}"

    # Approve is disabled while claims are unchecked (read from a second tab, not counted)
    other = new_page(browser, base)
    other.goto(f"{base}/cases/{cid}?all=1")
    assert other.get_by_role("button", name="Approve and send").is_disabled()
    other.close()

    # edit the last claim, remove claims whose quote was not found, confirm the rest with Tab and Enter
    claims = page.locator("li.claim")
    last = claims.nth(claims.count() - 1)
    n.click(last.locator("summary", has_text="Edit"))
    n.fill(last.locator("textarea"), "The customer reports a problem with the account.")
    n.click(last.get_by_role("button", name="Save"))
    page.wait_for_load_state("networkidle")
    while page.locator("li.claim", has_text="Quote not found in the note").filter(has=page.locator(".chip", has_text="Not checked yet")).count():
        n.click(page.locator("li.claim", has_text="Quote not found in the note").filter(has=page.locator(".chip", has_text="Not checked yet")).first
                .get_by_role("button", name="Remove"))
        page.wait_for_load_state("networkidle")
    while page.locator("button.confirm").count():
        assert n.confirm_by_keyboard()
    assert page.locator(".stepper a", has_text="confirmed").inner_text().count("of")

    # handover: fill what is missing, save
    n.click(page.get_by_role("link", name="Next: handover"))
    page.wait_for_load_state("networkidle")
    empties = page.locator(".fields input")
    for i in range(empties.count()):
        if not empties.nth(i).input_value():
            n.fill(empties.nth(i), "Checked")
    n.click(page.get_by_role("button", name="Save handover"))
    page.wait_for_load_state("networkidle")
    assert page.locator(".stepper a", has_text="0 missing").count() == 1
    n.click(page.get_by_role("link", name="Next: decide"))
    page.wait_for_load_state("networkidle")
    approve = page.get_by_role("button", name="Approve and send")
    assert approve.is_enabled()
    n.click(approve)
    expect(page.locator("#bar-text")).to_contain_text("Waiting for")
    assert db_value(dbfile, "SELECT state FROM cases WHERE id=?", cid) == "handed_over"
    SHOTS.mkdir(parents=True, exist_ok=True)
    (SHOTS / "flow-counts.json").write_text(json.dumps({"clicks": n.clicks, "keystrokes": n.keys, "case_id": cid}, indent=1) + "\n")
    print("FLOW COUNTS", n.clicks, "clicks", n.keys, "keystrokes", cid)

    # specialist: same page, same URL; returns; handler sees it Returned
    url = page.url
    switch(page, "Specialist")
    assert page.url == url
    page.goto(url)
    assert page.get_by_role("button", name="Accept").is_visible() and not page.get_by_role("button", name="Approve and send").count()
    page.locator("summary", has_text="Return to the handler").click()
    page.get_by_label("Reason").last.fill("Police reference does not match.")
    page.get_by_role("button", name="Return", exact=True).click()
    expect(page.locator("#bar-text")).to_contain_text("Nothing for you")
    switch(page, "Handler")
    page.goto(base + "/queue")
    page.goto(base + "/queue?owner=me&state=returned&department=Fraud+claims")
    row = page.locator(f'tr[data-case="{cid}"]')  # not first: an older returned case of H1 is above it
    assert "Returned" in row.inner_text()
    # resend, then the specialist returns again: the team lead owns it
    row.locator("a").click()
    page.get_by_role("button", name="Start review").click()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Approve and send").click()
    expect(page.locator("#bar-text")).to_contain_text("Waiting for")
    switch(page, "Specialist")
    page.locator("summary", has_text="Return to the handler").click()
    page.get_by_label("Reason").last.fill("Still the wrong reference.")
    page.get_by_role("button", name="Return", exact=True).click()
    expect(page.locator("#bar-text")).to_contain_text("Nothing for you")
    assert db_value(dbfile, "SELECT owner_id FROM cases WHERE id=?", cid) == "T1"
    switch(page, "Team lead")
    assert "Owner: T1" in page.locator(".case-head").inner_text()
    assert not page.errors, page.errors
    page.close()


def test_reject_needs_reason_and_help_panel(base, dbfile, browser):
    cid = candidates(dbfile)[1]
    page = new_page(browser, base)
    page.goto(f"{base}/cases/{cid}")
    page.locator("summary", has_text="Reject the draft").click()
    page.get_by_role("button", name="Reject draft").click()
    page.wait_for_selector("text=Enter a reason")
    page.get_by_role("button", name="How this page works").click()
    assert page.locator("#help").is_visible()
    page.keyboard.press("Escape")
    assert not page.locator("#help").is_visible()
    assert page.evaluate("document.activeElement.getAttribute('data-open')") == "help"
    page.close()


@pytest.mark.parametrize("width", [1440, 1100, 1024])
def test_case_in_browser(base, dbfile, browser, width):
    cid = candidates(dbfile)[2]
    page = new_page(browser, base, width)
    page.goto(f"{base}/cases/{cid}")
    page.wait_for_load_state("networkidle")
    if width == 1440:  # mid-check: one claim confirmed
        page.locator("button.confirm").first.click()
        expect(page.locator(".stepper a").first).to_contain_text("1 of")
    for url in (f"{base}/cases/{cid}", f"{base}/cases/{cid}?all=1"):
        page.goto(url)
        page.wait_for_load_state("networkidle")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"sideways scroll {url}"
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.className") == "skip"
        outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth")
        assert not outline.startswith("none") and not outline.endswith(" 0px"), outline
        page.evaluate("""window.ctl = [...document.querySelectorAll('a[href], button, summary, select, input:not([type=hidden]), textarea')]
            .filter(e => e.checkVisibility() && !e.disabled)""")
        wanted = page.evaluate("window.ctl.length")
        seen = set()
        for _ in range(wanted + 5):
            seen.add(page.evaluate("window.ctl.indexOf(document.activeElement)"))
            page.keyboard.press("Tab")
        seen.discard(-1)
        assert len(seen) == wanted, (url, len(seen), wanted)
    assert not page.errors, page.errors
    assert page.hosts <= {base.split("/")[2]}, page.hosts
    page.close()
