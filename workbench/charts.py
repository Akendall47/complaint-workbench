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


def step_line(series, title="", summary="") -> Markup:
    """A step line over (label, value) points in order, each point labelled with its value."""
    if not series:
        return EMPTY
    n, top, H = len(series), max(v for _, v in series) or 1, 170
    xs = [30 + (W - 60) * (i / (n - 1) if n > 1 else .5) for i in range(n)]
    ys = [30 + (H - 70) * (1 - v / top) for _, v in series]
    path = f"M{xs[0]:.1f},{ys[0]:.1f}" + "".join(f" H{xs[i]:.1f} V{ys[i]:.1f}" for i in range(1, n))
    every = max(1, -(-n // 10))
    body = [f'<line class="axis" x1="10" y1="{H - 40}" x2="{W - 10}" y2="{H - 40}" aria-hidden="true"/>',
            f'<path class="step" d="{path}" aria-hidden="true"/>']
    for i, (k, v) in enumerate(series):
        body.append(f'<circle class="dot" cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="4" aria-hidden="true"/>'
                    f'<text class="lbl halo" x="{xs[i]:.1f}" y="{ys[i] - 10:.1f}" text-anchor="middle">{_e(v)}</text>')
        if i % every == 0:
            body.append(f'<text class="lbl" x="{xs[i]:.1f}" y="{H - 14}" text-anchor="middle">{_e(k)}</text>')
    return _fig("".join(body), H, title, summary, ["Point", "Value"], series)


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


def sparkline(values, title="") -> Markup:
    """A small line with no table: the values are in the label. Used beside a figure that already shows them."""
    if not values:
        return EMPTY
    n, top = len(values), max(values) or 1
    pts = " ".join(f"{2 + 116 * (i / (n - 1) if n > 1 else .5):.1f},{22 - 20 * v / top:.1f}" for i, v in enumerate(values))
    label = _e(f"{title}: {', '.join(map(str, values))}" if title else ", ".join(map(str, values)))
    return Markup(f'<svg class="spark" viewBox="0 0 120 24" role="img" aria-label="{label}"><polyline class="step" points="{pts}"/></svg>')


def band_flow(left, right, bands, marks=(), title="", summary="") -> Markup:
    """Bands from left labels to right labels. bands: (left, right, count, href[, kind]); the kind is a class, so two paths between the same labels both show. Each band is a link with a title and a drawn count.
    Marked bands (left, right) get a heavier colour and the word rising. Minimum band width 3."""
    if not bands:
        return EMPTY
    bands = [(*b, "") if len(b) == 4 else tuple(b) for b in bands]
    top = max(b[2] for b in bands) or 1
    thick = lambda c: max(3.0, 30 * c / top)  # noqa: E731
    slot = lambda c: max(thick(c), 18.0) + 4  # noqa: E731  room for the drawn count
    ypos, ends = {}, {}
    for side, names, idx in (("l", left, 0), ("r", right, 1)):
        y = 6.0
        for name in names:
            start = y
            for i, b in enumerate(bands):
                if b[idx] == name:
                    ypos[(side, i)] = y + slot(b[2]) / 2
                    y += slot(b[2])
            ends[(side, name)] = (start + y) / 2 if y > start else None
            y += 12 if y > start else 0
        ends[side] = y
    H = int(max(ends["l"], ends["r"]) + 6)
    body = []
    for side, names, x, anchor in (("l", left, 170, "end"), ("r", right, 470, "start")):
        for name in names:
            if ends[(side, name)] is not None:
                body.append(f'<text class="lbl" x="{x}" y="{ends[(side, name)] + 5:.1f}" text-anchor="{anchor}">{_e(name)}</text>')
    marks = set(map(tuple, marks))
    for i, (l, r, c, href, kind) in enumerate(bands):
        y1, y2, mk = ypos[("l", i)], ypos[("r", i)], (l, r) in marks
        label = f"{l} to {r}: {c}" + (", rising" if mk else "") + (f", {kind}" if kind else "")
        body.append(f'<a href="{_e(href)}"><title>{_e(label)}</title>'
                    f'<path class="band{" mark" if mk else ""}{" " + _e(kind) if kind else ""}" d="M180,{y1:.1f} C320,{y1:.1f} 320,{y2:.1f} 460,{y2:.1f}" fill="none" stroke-width="{thick(c):.1f}"/>'
                    f'<text class="lbl halo" x="320" y="{(y1 + y2) / 2 + 5:.1f}" text-anchor="middle">{"▲ " if mk else ""}{_e(c)}</text></a>')
    return _fig("".join(body), H, title, summary, ["From", "To", "Count", "Marked"],
                [(l, r, c, "rising" if (l, r) in marks else kind) for l, r, c, _, kind in bands])
