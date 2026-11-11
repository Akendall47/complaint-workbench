"""A read-only static copy of the workbench, for hosts that only serve files (GitHub Pages). Each role gets its own folder of
pre-rendered pages; links between them are rewritten to files, and buttons and forms are switched off because no server
is behind them. Run from the repo root: uv run python tools/export_static.py   (writes site/, which is git-ignored)"""
import html
import re
import shutil
import tempfile
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from workbench.app import create_app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
ROLES = {"team-lead": ("team_lead", "T1"), "handler": ("handler", "H1"), "specialist": ("specialist", "S1")}
START = ["/", "/queue", "/cases/AB-2026-00768", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"]
LIMIT = 140  # pages per role: every view, its main filters and the cases linked from the first screens
HREF = re.compile(r'href="([^"]*)"')
NOTE = "Read-only preview: buttons and forms are off here. Run the app for the full product. Not an Ankura product. All data synthetic."


def page_file(url: str) -> str:
    """'/queue?owner=all' -> 'queue--owner-all.html'; '/' -> 'index.html'."""
    u = urlsplit(url)
    base = u.path.strip("/").replace("/", "-") or "index"
    return base + ("--" + re.sub(r"[^A-Za-z0-9]+", "-", u.query).strip("-") if u.query else "") + ".html"


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


def rewrite(text: str, url: str, role: str, sites: dict) -> str:
    pages = sites[role]

    def link(m):
        h = html.unescape(m.group(1))
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
    text = re.sub(r'<script src="\.\./static/htmx\.min\.js"[^>]*></script>\s*', "", text)
    text = re.sub(r"""\s(hx-[a-z-]+)=("[^"]*"|'[^']*')""", "", text)  # no server behind the page: plain links only
    # the role switch becomes links to the same page in the other role's folder
    def role_link(m):
        r = m.group(1)
        folder = next(k for k, v in ROLES.items() if v[0] == r)
        target = page_file(url) if url in sites[folder] else "index.html"
        return f'<a href="../{folder}/{target}" class="role-btn" aria-pressed="{m.group(2)}">{m.group(3)}</a>'
    text = re.sub(r'<button type="submit" name="role" value="(\w+)" aria-pressed="(\w+)">([^<]*)</button>', role_link, text)
    text = re.sub(r'<form class="role-form"[^>]*>', '<div class="role-form">', text).replace("</form>\n  <button type=\"button\" class=\"help-button\"", "</div>\n  <button type=\"button\" class=\"help-button\"", 1)
    # every other button and field does nothing without the server, so it says so instead of failing
    text = re.sub(r"<button(?![^>]*data-(?:open|close))", '<button disabled title="Read-only preview"', text)
    text = re.sub(r'<(input|select|textarea)(?![^>]*type="(?:radio|hidden)")', r'<\1 disabled', text)
    text = re.sub(r'<footer class="footer">.*?</footer>', f'<footer class="footer">{NOTE}</footer>', text, flags=re.S)
    return text.replace("</head>", '<link rel="stylesheet" href="../static/static-site.css">\n</head>', 1)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "workbench.db"
        shutil.copy(ROOT / "data" / "workbench.db", db)
        app = create_app(str(db))
        sites = {}
        for folder, (role, staff) in ROLES.items():
            client = TestClient(app, base_url="http://127.0.0.1:8000")
            client.cookies.update({"role": role, "staff_id": staff})
            sites[folder] = crawl(client)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "workbench" / "static", OUT / "static")
    (OUT / "static" / "static-site.css").write_text(
        ".role-btn{display:inline-flex;align-items:center;min-height:30px;padding:4px 10px;border-radius:10px;color:#3f404a;font-size:13px;text-decoration:none;white-space:nowrap}\n"
        ".role-btn[aria-pressed=true]{background:white;color:var(--ink);font-weight:600;box-shadow:var(--shadow)}\n"
        "button[disabled],input[disabled],select[disabled],textarea[disabled]{cursor:not-allowed}\n", encoding="utf-8")
    for folder, pages in sites.items():
        (OUT / folder).mkdir(parents=True)
        for url, text in pages.items():
            (OUT / folder / page_file(url)).write_text(rewrite(text, url, folder, sites), encoding="utf-8")
    (OUT / "index.html").write_text('<!DOCTYPE html><meta charset="utf-8"><title>Complaint Workbench</title>'
                                    '<meta http-equiv="refresh" content="0; url=team-lead/index.html"><a href="team-lead/index.html">Open the workbench</a>', encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are
    print({k: len(v) for k, v in sites.items()}, "pages written to", OUT)


if __name__ == "__main__":
    main()
