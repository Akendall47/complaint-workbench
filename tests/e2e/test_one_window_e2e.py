"""Every page fits one window at common laptop and desktop sizes, for every role: no page scroll, no sideways scroll, and every
panel stays inside the window. Long lists scroll inside their own panel. Run on its own: uv run pytest tests/e2e -o addopts=""."""
import pytest

PAGES = ["/", "/queue", "/cases/AB-2026-00768", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"]
ROLES = {"handler": "H1", "specialist": "S1", "team_lead": "T1"}
SIZES = [(1366, 768), (1920, 1080)]

FITS = """() => {
  const d = document.documentElement, out = [];
  if (d.scrollHeight > innerHeight + 1) out.push('page scrolls ' + d.scrollHeight + ' > ' + innerHeight);
  if (d.scrollWidth > innerWidth + 1) out.push('sideways ' + d.scrollWidth);
  for (const p of document.querySelectorAll('.panel')) {
    const r = p.getBoundingClientRect();
    if (r.bottom > innerHeight + 1 || r.right > innerWidth + 1) out.push('panel outside: ' + (p.querySelector('h2') || p).textContent.trim().slice(0, 40));
  }
  return out;
}"""


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("role", list(ROLES))
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_page_fits_one_window(base, browser, path, role, size):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
    ctx.add_cookies([{"name": "role", "value": role, "url": base}, {"name": "staff_id", "value": ROLES[role], "url": base}])
    page = ctx.new_page()
    page.goto(base + path)
    page.wait_for_load_state("networkidle")
    assert page.evaluate(FITS) == []
    ctx.close()


@pytest.mark.parametrize("path", PAGES)
def test_phone_width_has_no_sideways_scroll(base, browser, path):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(base + path)
    page.wait_for_load_state("networkidle")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.close()
