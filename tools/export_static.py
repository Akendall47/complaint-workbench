"""A static copy of the workbench, for hosts that only serve files (GitHub Pages). Each role gets its own folder of
pre-rendered pages; links between them are rewritten to files. One case, the demo case, is recorded from start to finish
with the real app (claims confirmed, handover saved, approved, then accepted by the specialist), so on that case every
button that moves it on works. Other buttons say they need the full app.
Run from the repo root: uv run python tools/export_static.py   (writes site/, which is git-ignored)"""
import html
import json
import re
import shutil
import sqlite3
import tempfile
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from workbench.app import create_app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
BASE = "http://127.0.0.1:8000"
ROLES = {"team-lead": ("team_lead", "T1"), "handler": ("handler", "H1"), "specialist": ("specialist", "S1")}
DEMO = "AB-2026-00768"
START = ["/", "/queue", f"/cases/{DEMO}", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"]
LIMIT = 140  # pages per role: every view, its main filters and the cases linked from the first screens
HREF = re.compile(r'href="([^"]*)"')
NOTE = (f"Preview: on case {DEMO} (as Handler) every button that moves the case on works. Other buttons need the full app. "
        "Not an Ankura product. All data synthetic.")
CSS = """.role-btn{display:inline-flex;align-items:center;min-height:30px;padding:4px 10px;border-radius:10px;color:#3f404a;font-size:13px;text-decoration:none;white-space:nowrap}
.role-btn[aria-pressed=true]{background:white;color:var(--ink);font-weight:600;box-shadow:var(--shadow)}
button[disabled],input[disabled],select[disabled],textarea[disabled]{cursor:not-allowed}
[data-goto]{outline:3px solid rgba(91,87,214,.45);outline-offset:2px}
"""
JS = """// The recorded demo case: a button marked data-goto opens the page the real app showed after that action.
document.addEventListener('click', function (e) {
  var b = e.target.closest('[data-goto]');
  if (b) { e.preventDefault(); location.href = b.getAttribute('data-goto'); }
});
"""


def page_file(url: str) -> str:
    """'/queue?owner=all' -> 'queue--owner-all.html'; '/' -> 'index.html'."""
    u = urlsplit(url)
    base = u.path.strip("/").replace("/", "-") or "index"
    return base + ("--" + re.sub(r"[^A-Za-z0-9]+", "-", u.query).strip("-") if u.query else "") + ".html"


def client_for(app, role: str) -> TestClient:
    c = TestClient(app, base_url=BASE, headers={"Origin": BASE})  # same origin, as a browser on the app would send
    c.cookies.update({"role": ROLES[role][0], "staff_id": ROLES[role][1]})
    return c


def crawl(client) -> dict:
    """Breadth first from the main views, so every view and its first links are kept before deeper ones."""
    pages, todo, seen = {}, deque(START), set(START)
    while todo and len(pages) < LIMIT:
        url = todo.popleft()
        r = client.get(url)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        pages[url] = r.text
        for h in HREF.findall(r.text):
            h = html.unescape(h).split("#")[0]
            if h.startswith("/") and not h.startswith("/static/") and h not in seen:
                seen.add(h)
                todo.append(h)
    return pages


def form_of(text: str, action: str) -> str:
    start = text.index(f'action="{action}"')
    return text[start:text.index("</form>", start)]


def fields(text: str, action: str) -> dict:
    """The values a browser would send from that form."""
    return {n: html.unescape(v) for n, v in re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', form_of(text, action))}


def journey(app, truth: dict) -> list[dict]:
    """The demo case pressed through for real. Each step: the role folder, the page, and what was pressed on it."""
    h, s = client_for(app, "handler"), client_for(app, "specialist")
    steps, url = [], f"/cases/{DEMO}"
    cur = h.get(url).text

    def press(client, folder, action, data=None):
        nonlocal cur, url
        steps.append({"folder": folder, "url": url, "html": cur, "form": action, "fill": data})
        r = client.post(action, data=data or fields(cur, action))
        assert r.status_code == 200, (action, r.status_code, r.text[:200])
        cur, url = r.text, str(r.url).replace(BASE, "")

    def follow(client, folder, href):
        nonlocal cur, url
        steps.append({"folder": folder, "url": url, "html": cur, "link": href})
        cur, url = client.get(href).text, href

    while True:  # every claim: confirm it, or remove it when its quote was not found
        pending = [b for b in cur.split('<li class="claim"')[1:] if "chip ok" not in b.split("</li>")[0]]
        if not pending:
            break
        m = re.search(r'action="([^"]+/confirm)"', pending[0]) or re.search(r'action="([^"]+/remove)"', pending[0])
        press(h, "handler", m.group(1))
    follow(h, "handler", f"/cases/{DEMO}?step=2")
    action = f"/cases/{DEMO}/handover"
    data = fields(cur, action)
    data.update({k: truth.get(k[2:], "Given by the customer").lstrip("£") for k, v in data.items() if k.startswith("f_") and not v})
    press(h, "handler", action, data)
    follow(h, "handler", f"/cases/{DEMO}?step=3")
    press(h, "handler", f"/cases/{DEMO}/approve")
    steps.append({"folder": "handler", "url": url, "html": cur, "role": "specialist"})
    url = f"/cases/{DEMO}?step=3"
    cur = s.get(url).text
    press(s, "specialist", f"/cases/{DEMO}/accept")
    steps.append({"folder": "specialist", "url": url, "html": cur})
    return steps


def mark(steps: list[dict]) -> list[dict]:
    """Point the pressed control on each step at the next step's file, before the generic rewrite."""
    for i, st in enumerate(steps):
        st["file"] = page_file(f"/cases/{DEMO}") if i == 0 else f"journey-{i}.html"
    for i, st in enumerate(steps[:-1]):
        nxt = steps[i + 1]
        target = nxt["file"] if nxt["folder"] == st["folder"] else f"../{nxt['folder']}/{nxt['file']}"
        t = st["html"]
        if "form" in st:
            at = t.index(f'action="{st["form"]}"')
            b = t.index("<button", at)
            t = t[:b] + f'<button data-goto="{target}"' + t[b + 7:].replace(" disabled", "", 1) if " disabled" in t[b:t.index(">", b)] else t[:b] + f'<button data-goto="{target}"' + t[b + 7:]
            if st.get("fill"):  # show the handover values that were saved
                for k, v in st["fill"].items():
                    t = t.replace(f'name="{k}" value=""', f'name="{k}" value="{html.escape(v)}"', 1)
        elif "link" in st:
            t = t.replace(f'href="{html.escape(st["link"])}"', f'href="journey:{target}" data-goto="{target}"')  # the step tab and the bottom bar
        elif "role" in st:
            st["role_goto"] = target
        st["html"] = t
    return steps


def rewrite(text: str, url: str, role: str, sites: dict, role_goto: str = "") -> str:
    pages = sites[role]

    def link(m):
        h = html.unescape(m.group(1))
        if h.startswith("journey:"):
            return f'href="{h[8:]}"'
        if h.startswith("/static/"):
            return f'href="../static/{h[8:]}"'
        if not h.startswith("/"):
            return m.group(0)
        path, _, frag = h.partition("#")
        target = path if path in pages else urlsplit(path).path if urlsplit(path).path in pages else None
        if target is None:
            return 'href="#" aria-disabled="true"'
        return f'href="{page_file(target)}{"#" + frag if frag else ""}"'

    text = HREF.sub(link, text)
    text = text.replace('src="/static/', 'src="../static/')
    text = re.sub(r'<script src="\.\./static/htmx\.min\.js"[^>]*></script>\s*', '<script src="../static/static-site.js" defer></script>\n', text)
    text = re.sub(r"""\s(hx-[a-z-]+)=("[^"]*"|'[^']*')""", "", text)  # no server behind the page: plain links only

    def role_link(m):  # the role switch becomes links to the same page in the other role's folder
        r = m.group(1)
        folder = next(k for k, v in ROLES.items() if v[0] == r)
        target = role_goto if role_goto and folder == "specialist" else page_file(url) if url in sites[folder] else "index.html"
        goto = ' data-goto="' + role_goto + '"' if role_goto and folder == "specialist" else ""
        return f'<a href="../{folder}/{target}" class="role-btn" aria-pressed="{m.group(2)}"{goto}>{m.group(3)}</a>'
    text = re.sub(r'<button type="submit" name="role" value="(\w+)" aria-pressed="(\w+)">([^<]*)</button>', role_link, text)
    text = re.sub(r'<form class="role-form"[^>]*>', '<div class="role-form">', text).replace("</form>\n  <button type=\"button\" class=\"help-button\"", "</div>\n  <button type=\"button\" class=\"help-button\"", 1)
    # other buttons and fields need the server, so they say so instead of failing
    text = re.sub(r"<button(?![^>]*data-(?:open|close|goto))", f'<button disabled title="Needs the full app. Try case {DEMO} as Handler."', text)
    text = re.sub(r'<(input|select|textarea)(?![^>]*type="(?:radio|hidden)")', r'<\1 disabled', text)
    text = re.sub(r'<footer class="footer">.*?</footer>', f'<footer class="footer">{NOTE}</footer>', text, flags=re.S)
    return text.replace("</head>", '<link rel="stylesheet" href="../static/static-site.css">\n</head>', 1)


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # the apps may still hold their databases open on Windows
        for name in ("crawl.db", "journey.db"):  # the crawl sees the untouched data; the journey changes its own copy
            shutil.copy(ROOT / "data" / "workbench.db", Path(tmp) / name)
        with sqlite3.connect(Path(tmp) / "journey.db") as c:
            truth = json.loads(c.execute("SELECT handover_true_json FROM cases WHERE id = ?", (DEMO,)).fetchone()[0] or "{}")
        app = create_app(str(Path(tmp) / "crawl.db"))
        sites = {folder: crawl(client_for(app, folder)) for folder in ROLES}
        steps = mark(journey(create_app(str(Path(tmp) / "journey.db")), truth))
    OUT.mkdir(exist_ok=True)
    for child in OUT.iterdir():  # keep .git: site/ is also the clone of the published Pages repo
        if child.name != ".git":
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(ROOT / "workbench" / "static", OUT / "static")
    (OUT / "static" / "static-site.css").write_text(CSS, encoding="utf-8")
    (OUT / "static" / "static-site.js").write_text(JS, encoding="utf-8")
    for folder, pages in sites.items():
        (OUT / folder).mkdir(parents=True)
        for url, text in pages.items():
            (OUT / folder / page_file(url)).write_text(rewrite(text, url, folder, sites), encoding="utf-8")
    for st in steps:  # written last, so the demo case's first page replaces its read-only copy
        (OUT / st["folder"] / st["file"]).write_text(rewrite(st["html"], st["url"], st["folder"], sites, st.get("role_goto", "")), encoding="utf-8")
    (OUT / "index.html").write_text('<!DOCTYPE html><meta charset="utf-8"><title>Complaint Workbench</title>'
                                    '<meta http-equiv="refresh" content="0; url=handler/queue.html"><a href="handler/queue.html">Open the workbench</a>', encoding="utf-8")
    deck = OUT / "deck"  # the five-page deck as a web page, plus the PDF
    (deck / "screenshots").mkdir(parents=True)
    page = (ROOT / "docs" / "deck" / "deck.html").read_text(encoding="utf-8")
    for shot in set(re.findall(r'\.\./screenshots/([\w-]+\.png)', page)):
        shutil.copy(ROOT / "docs" / "screenshots" / shot, deck / "screenshots" / shot)
    for asset in ("ankura-logo.svg", "ankura-logo-reverse.svg", "vault-graph-dark.svg"):
        shutil.copy(ROOT / "docs" / "deck" / asset, deck / asset)
    (deck / "index.html").write_text(page.replace("../screenshots/", "screenshots/"), encoding="utf-8")
    shutil.copy(ROOT / "docs" / "deck.pdf", deck / "Complaint-Workbench-deck.pdf")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are
    print({k: len(v) for k, v in sites.items()}, f"pages; demo case journey: {len(steps)} steps; written to {OUT}")


if __name__ == "__main__":
    main()
