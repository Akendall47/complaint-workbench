"""The guard that keeps pages simple. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest


@pytest.mark.parametrize("path", ["/", "/queue", "/cases/AB-2026-00768", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"])
def test_every_view_is_calm_above_the_fold(base, browser, path):
    """At most 4 cards and 3 headings visible in the first 900px at 1440 wide."""
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.context.add_cookies([{"name": "role", "value": "team_lead", "url": base}, {"name": "staff_id", "value": "T1", "url": base}])
    page.goto(base + path)
    page.wait_for_load_state("networkidle")
    cards, heads = page.evaluate("""() => {
      const seen = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < window.innerHeight; };
      return [[...document.querySelectorAll('main .card, main .table-card')].filter(seen).length, [...document.querySelectorAll('main h2')].filter(seen).length];
    }""")
    assert cards <= 4 and heads <= 3, (path, cards, heads)
    page.close()
