"""Fluid charts for the one-window pages. They stretch to fill their card: the outer drawing has no viewBox and places things
in percent, lines and areas sit in a nested 0-100 drawing that may stretch, strokes keep their width, and text keeps its CSS
size. No script, no inline style. Numbers sit in a visually hidden table for screen readers; hover titles show them to others."""
from markupsafe import Markup

from .charts import EMPTY, WEEKDAYS, _e


def _table(head, rows) -> str:
    th = "".join(f'<th scope="col">{_e(c)}</th>' for c in head)
    tr = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="sr-only"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def _pct(v: float) -> str:
    return (f"{v:.2f}".rstrip("0").rstrip(".") or "0") + "%"


def track(items, hot=(), href=None, cls=None) -> Markup:
    """Horizontal bars on a grey track, one row per (label, value): label, bar, value. `hot` labels use the warm colour,
    `href(label)` makes the label a link, `cls(label)` adds a colour class to the bar (stage colours)."""
    if not items:
        return EMPTY
    top, rows = max(v for _, v in items) or 1, []
    for k, v in items:
        name = f'<a class="tk-label" href="{_e(href(k))}">{_e(k)}</a>' if href else f'<span class="tk-label">{_e(k)}</span>'
        extra = (" hot" if k in hot else "") + (f" {cls(k)}" if cls else "")
        rows.append(f'<li>{name}<svg class="tk-bar" aria-hidden="true" focusable="false"><rect class="tk-bg" width="100%" height="100%" rx="5"/>'
                    f'<rect class="tk-fill{extra}" width="{_pct(100 * v / top)}" height="100%" rx="5"/></svg><b class="tk-val">{v:,}</b></li>')
    return Markup(f'<ul class="track">{"".join(rows)}</ul>')


def area(points, label: str, ticks: int = 6) -> Markup:
    """Stepped area over (day label, value) points in order, the peak marked with its value, about `ticks` labels under it."""
    if not points or not any(v for _, v in points):
        return EMPTY
    n, top = len(points), max(v for _, v in points)
    y = lambda v: 100 - 80 * v / top  # noqa: E731  (headroom keeps the peak label inside the card)
    d = "".join(f"{'M' if i == 0 else 'L'}{100 * i / n:.2f} {y(v):.2f}H{100 * (i + 1) / n:.2f}" for i, (_, v) in enumerate(points))
    peak = max(range(n), key=lambda i: (points[i][1], i))
    px, anchor = 100 * (peak + .5) / n, "end" if peak > n * .85 else "start" if peak < n * .15 else "middle"
    grid = "".join(f'<line class="gridline" x1="0" x2="100%" y1="{g}%" y2="{g}%"/>' for g in (20, 60, 100))
    axis = "".join(f"<span>{_e(points[i][0])}</span>" for i in range(0, n, max(1, round(n / ticks))))
    return Markup(f'<figure class="area-chart" role="img" aria-label="{_e(label)}"><div class="plot"><svg aria-hidden="true" focusable="false">{grid}'
                  f'<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">'
                  f'<path class="area-fill" d="{d}V100H0Z"/><path class="area-line" d="{d}" vector-effect="non-scaling-stroke"/></svg>'
                  f'<circle class="peak-dot" cx="{_pct(px)}" cy="{_pct(y(points[peak][1]))}" r="3.5"/>'
                  f'<text class="peak-lbl" x="{_pct(px)}" y="{_pct(y(points[peak][1]))}" dy="-9" text-anchor="{anchor}">{points[peak][1]}</text>'
                  f'</svg></div><div class="x-axis">{axis}</div>{_table(["Day", "Value"], points)}</figure>')


def heat(grid, hours, label: str) -> Markup:
    """Weekday rows by hour columns as rounded cells in five shades, with a legend. Counts are in each cell's title."""
    if not grid or not any(any(r) for r in grid):
        return EMPTY
    top, every = max(max(r) for r in grid), 1 if len(hours) <= 12 else 3
    cells = ['<span></span>'] + [f'<span class="hh">{h if (h - hours[0]) % every == 0 else ""}</span>' for h in hours]
    for r, row in enumerate(grid):
        cells.append(f'<span class="hd">{WEEKDAYS[r]}</span>')
        cells += [f'<span class="hc l{min(4, -(-4 * v // top))}" title="{WEEKDAYS[r]} {h:02d}:00, {v} received"></span>' for h, v in zip(hours, row)]
    legend = "".join(f'<i class="hc l{i}"></i>' for i in range(5))
    return Markup(f'<figure class="heat-chart" role="img" aria-label="{_e(label)}"><div class="heat h{len(hours)}">{"".join(cells)}</div>'
                  f'<div class="legend">Fewer {legend} More</div>'
                  f'{_table(["Day"] + [f"{h:02d}:00" for h in hours], [[WEEKDAYS[r]] + list(row) for r, row in enumerate(grid)])}</figure>')


def spark(values, label: str) -> Markup:
    """A small line with a tinted area under it; the label lists the values."""
    if not values:
        return Markup("")
    n, top = len(values), max(values) or 1
    pts = [f"{100 * i / (n - 1 or 1):.1f},{29 - 26 * v / top:.1f}" for i, v in enumerate(values)]
    return Markup(f'<svg class="spark" viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label="{_e(label)}">'
                  f'<path d="M0,30 L{" L".join(pts)} L100,30Z"/><polyline points="{" ".join(pts)}" vector-effect="non-scaling-stroke"/></svg>')


def cols(items, label: str, hot=()) -> Markup:
    """Vertical columns over (label, value) in order: the value above each column, the labels in a row under the drawing."""
    if not items:
        return EMPTY
    n, top, out = len(items), max(v for _, v in items) or 1, []
    for i, (k, v) in enumerate(items):
        h, x, w = 70 * v / top, 100 * i / n, 100 / n
        out.append(f'<rect class="col{" hot" if k in hot else ""}" x="{_pct(x + w * .2)}" y="{_pct(100 - h)}" width="{_pct(w * .6)}" height="{_pct(max(h, 1))}" rx="4"/>'
                   f'<text class="col-val" x="{_pct(x + w / 2)}" y="{_pct(100 - h)}" dy="-5" text-anchor="middle">{v}</text>')
    names = "".join(f"<span>{_e(k)}</span>" for k, _ in items)
    return Markup(f'<figure class="cols-chart" role="img" aria-label="{_e(label)}"><div class="plot"><svg aria-hidden="true" focusable="false">'
                  f'{"".join(out)}</svg></div><div class="x-axis even">{names}</div>{_table(["Item", "Value"], items)}</figure>')


def _stack(totals: dict, gap=3.0, least=6.0) -> dict:
    """Top and height (in percent) for each key, largest first. Every node gets at least `least` so labels never collide."""
    free, s, y, out = 100 - gap * (len(totals) - 1) - least * len(totals), sum(totals.values()) or 1, 0.0, {}
    for k, c in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])):
        h = least + free * c / s
        out[k] = [y, h, y]  # top, height, where the next band starts
        y += h + gap
    return out


def band_map(rows, href=None, label="") -> Markup:
    """Departments on the left, complaint types on the right, one band per (department, type, open cases), width by cases."""
    if not rows:
        return EMPTY
    left, right = {}, {}
    for d, t, c in rows:
        left[d], right[t] = left.get(d, 0) + c, right.get(t, 0) + c
    L, R = _stack(left), _stack(right)
    order = {**{k: i for i, k in enumerate(L)}, **{k: i for i, k in enumerate(R)}}
    bands = []
    for d, t, c in sorted(rows, key=lambda r: (order[r[0]], order[r[1]])):
        a, b = L[d][1] * c / left[d], R[t][1] * c / right[t]
        y0, y1 = L[d][2], R[t][2]
        L[d][2], R[t][2] = y0 + a, y1 + b
        band = (f'<path class="mband" d="M3 {y0:.2f}C50 {y0:.2f} 50 {y1:.2f} 97 {y1:.2f}V{y1 + b:.2f}C50 {y1 + b:.2f} 50 {y0 + a:.2f} 3 {y0 + a:.2f}Z">'
                f'<title>{_e(d)} to {_e(t)}: {c} open</title></path>')
        bands.append(f'<a href="{_e(href(d, t))}">{band}</a>' if href else band)
    nodes = "".join(f'<rect class="node" x="0" y="{v[0]:.2f}" width="3" height="{v[1]:.2f}"/>' for v in L.values())
    nodes += "".join(f'<rect class="node t" x="97" y="{v[0]:.2f}" width="3" height="{v[1]:.2f}"/>' for v in R.values())
    labels = "".join(f'<text class="lbl" x="{x}" y="{_pct(v[0] + v[1] / 2)}" dx="{dx}" dy="4" text-anchor="{anchor}">{_e(k)} <tspan class="cnt">{tot[k]}</tspan></text>'
                     for tot, nodes_, x, anchor, dx in ((left, L, "33%", "end", -6), (right, R, "67%", "start", 6)) for k, v in nodes_.items())
    return Markup(f'<figure class="map"><svg role="group" aria-label="{_e(label)}">'
                  f'<svg x="33%" width="34%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">{"".join(bands)}{nodes}</svg>'
                  f'{labels}</svg>{_table(["Department", "Type", "Open"], rows)}</figure>')
