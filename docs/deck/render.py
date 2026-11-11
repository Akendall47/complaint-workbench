"""Render the five-slide deck to docs/deck.pdf and one PNG per slide, then check that no text overlaps other text or a picture,
and that nothing runs off its slide. Run from the repo root: uv run python docs/deck/render.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent

# Every box that shows text or a picture, per slide. Overlapping screenshots on purpose (slide 5) are allowed;
# text over text, text over a picture, and anything past the slide edge are not.
CHECK = """() => [...document.querySelectorAll('.slide')].map((slide, n) => {
  const s = slide.getBoundingClientRect(), out = [];
  const boxes = [...slide.querySelectorAll('*')].filter(e => {
    if (getComputedStyle(e).visibility === 'hidden') return false;
    if (e.tagName === 'IMG') return true;
    return [...e.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
  }).map(e => {
    const r = document.createRange(); r.selectNodeContents(e);
    const b = e.tagName === 'IMG' ? e.getBoundingClientRect() : r.getBoundingClientRect();
    return {e, b, img: e.tagName === 'IMG', name: (e.textContent || e.alt || e.src).trim().slice(0, 40)};
  });
  for (const x of boxes) {
    if (x.img && x.e.closest('.right')) continue;  // the slide 3 screenshot bleeds off the right edge on purpose
    if (x.b.left < s.left - 1 || x.b.right > s.right + 1 || x.b.top < s.top - 1 || x.b.bottom > s.bottom + 1) out.push('off slide: ' + x.name);
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    if (a.img && b.img) continue;
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const w = Math.min(a.b.right, b.b.right) - Math.max(a.b.left, b.b.left), h = Math.min(a.b.bottom, b.b.bottom) - Math.max(a.b.top, b.b.top);
    if (w > 2 && h > 2) out.push('overlap: "' + a.name + '" and "' + b.name + '"');
  }
  return [n + 1, out];
})"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto((HERE / "deck.html").resolve().as_uri())
    page.wait_for_load_state("networkidle")
    page.pdf(path=str(HERE.parent / "deck.pdf"), width="1920px", height="1080px", print_background=True)
    for i, slide in enumerate(page.query_selector_all(".slide"), 1):
        slide.screenshot(path=str(HERE / f"slide-{i}.png"))
    problems = [(n, out) for n, out in page.evaluate(CHECK) if out]
    browser.close()
print("wrote docs/deck.pdf and docs/deck/slide-1.png to slide-5.png")
for n, out in problems:
    print(f"slide {n}:", *out, sep="\n  ")
print("layout check:", "no overlaps" if not problems else f"{sum(len(o) for _, o in problems)} problems")
