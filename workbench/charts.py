"""Server-drawn SVG charts. No script, no inline style: looks come from classes in app.css.
Every chart is a figure: the drawing (role="img", aria-label with title and one-sentence summary) and the numbers as a table
inside <details>. An empty input gives <p class="empty">No data</p>, never an empty drawing."""
from markupsafe import Markup, escape

W = 640
EMPTY = Markup('<p class="empty">No data</p>')
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = range(8, 19)


def _e(v) -> str:
    return str(escape(v))


def _fig(body: str, h: int, title: str, summary: str, head: list, rows: list) -> Markup:
    label = _e(f"{title}. {summary}" if title and summary else title or summary or "Chart")
    th = "".join(f"<th scope=\"col\">{_e(c)}</th>" for c in head)
    tr = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return Markup(f'<figure class="chart"><svg class="chart-svg" viewBox="0 0 {W} {h}" role="img" aria-label="{label}">{body}</svg>'
                  f'<details class="chart-data"><summary>Show the numbers</summary><div class="table-wrap"><table class="case-table">'
                  f'<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details></figure>')


def bars(items, highlight=None, title="", summary="") -> Markup:
    """Horizontal bars, one per (label, value). The highlighted label is bold and outlined, and the table says so."""
    if not items:
        return EMPTY
    top, body = max(v for _, v in items) or 1, []
    for i, (k, v) in enumerate(items):
        y, w, hi = i * 30 + 4, 400 * v / top, k == highlight
        body.append(f'<text class="lbl{" hi" if hi else ""}" x="170" y="{y + 16}" text-anchor="end">{_e(k)}</text>'
                    f'<rect class="bar{" hi" if hi else ""}" x="180" y="{y}" width="{max(w, 1):.1f}" height="22" aria-hidden="true"/>'
                    f'<text class="lbl{" hi" if hi else ""}" x="{186 + w:.1f}" y="{y + 16}">{_e(v)}</text>')
    return _fig("".join(body), len(items) * 30 + 8, title, summary, ["Item", "Value", "Marked"],
                [(k, v, "yes" if k == highlight else "") for k, v in items])


def columns(series, title="", summary="", axis="") -> Markup:
    """Vertical columns over (label, value) points in order, the value above each column. The axis caption sits under the labels."""
    if not series:
        return EMPTY
    n, top, base = len(series), max(v for _, v in series) or 1, 118  # 170 high in all: the page shows it at a fixed 160px
    slot = (W - 20) / n
    body = [f'<line class="axis" x1="10" y1="{base}" x2="{W - 10}" y2="{base}" aria-hidden="true"/>']
    for i, (k, v) in enumerate(series):
        h, x = max(2.0, 90 * v / top), 10 + i * slot + slot * .2
        body.append(f'<rect class="bar" x="{x:.1f}" y="{base - h:.1f}" width="{slot * .6:.1f}" height="{h:.1f}" aria-hidden="true"/>'
                    f'<text class="lbl" x="{x + slot * .3:.1f}" y="{base - h - 6:.1f}" text-anchor="middle">{_e(v)}</text>'
                    f'<text class="lbl" x="{x + slot * .3:.1f}" y="{base + 20}" text-anchor="middle">{_e(k)}</text>')
    if axis:
        body.append(f'<text class="lbl" x="{W / 2}" y="{base + 42}" text-anchor="middle">{_e(axis)}</text>')
    return Markup(_fig("".join(body), base + 52, title, summary, [axis or "Item", "Value"], series).replace("chart-svg", "chart-svg wide", 1))


def heatmap(grid, title="", summary="") -> Markup:
    """Weekday rows by hour columns (8 to 18). Each cell shows its count; the shade is a second cue."""
    if not grid or not any(any(r) for r in grid):
        return EMPTY
    top, body = max(max(r) for r in grid) or 1, []
    for c, h in enumerate(HOURS):
        body.append(f'<text class="lbl" x="{60 + c * 50 + 25}" y="16" text-anchor="middle">{h}</text>')
    for r, row in enumerate(grid):
        body.append(f'<text class="lbl" x="50" y="{r * 30 + 50}" text-anchor="end">{WEEKDAYS[r]}</text>')
        for c, v in enumerate(row):
            body.append(f'<rect class="cell l{min(4, round(4 * v / top))}" x="{60 + c * 50}" y="{r * 30 + 28}" width="48" height="28" aria-hidden="true"/>'
                        f'<text class="lbl" x="{60 + c * 50 + 24}" y="{r * 30 + 48}" text-anchor="middle">{_e(v)}</text>')
    return _fig("".join(body), 7 * 30 + 36, title, summary, ["Day"] + [f"{h}:00" for h in HOURS], [[WEEKDAYS[r]] + row for r, row in enumerate(grid)])
