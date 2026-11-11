"""Server-rendered case flow; geometry is independent of the CSS colour palette. It scales to fit its panel."""

from markupsafe import Markup, escape

from .charts import EMPTY


_KINDS = {
    "normal": "Normal path",
    "urgent": "Urgent fast path",
    "returned": "Returned for more work",
    "second_return": "Returned a second time",
}


def _e(value):
    return str(escape(value))


def _link(body, href):
    return f'<a href="{_e(href)}">{body}</a>' if href else body


def _box(text, x, y, font):
    width, height = len(text) * .6 * font, font * 1.2
    return (x - width / 2, y - height, x + width / 2, y)


def _near(a, b):
    return not (a[2] + 6 <= b[0] or b[2] + 6 <= a[0]
                or a[3] + 6 <= b[1] or b[3] + 6 <= a[1])


def _place(text, x, y, font, occupied):
    """Try nearby positions first, then extend downwards for crowded diagrams.

    All text uses an explicit baseline and middle anchor. Reserve estimated
    boxes plus a six-pixel gutter before emitting any SVG.
    """
    half = len(text) * .6 * font / 2
    x = max(half + 8, min(992 - half, x))
    for step in range(10000):
        offsets = (0,) if step == 0 else (step * 26, -step * 26)
        for dy in offsets:
            for dx in (0, -24, 24, -48, 48):
                nx, ny = round(x + dx, 2), round(y + dy, 2)
                box = _box(text, nx, ny, font)
                if box[0] < 8 or box[2] > 992 or box[1] < 8:
                    continue
                if not any(_near(box, other) for other in occupied):
                    occupied.append(box)
                    return nx, ny
    raise ValueError("Flow label is too wide for the viewBox")


def _text(text, x, y, classes, font):
    return (f'<text class="lbl {classes}" x="{x:g}" y="{y:g}" '
            f'text-anchor="middle" font-size="{font}">{_e(text)}</text>')


def case_flow(stages, paths, title="", summary="") -> Markup:
    """Draw ordered stage bars, count-scaled ribbons and an accessible table."""
    by_key = {stage["key"]: stage for stage in stages}
    paths = [p for p in paths if p["from"] in by_key and p["to"] in by_key]
    if not paths or not any(p.get("count", 0) > 0 for p in paths):
        return EMPTY

    main = [s for s in stages if s.get("row", "main") != "below"]
    below = [s for s in stages if s.get("row") == "below"]
    positions = {s["key"]: (100 + i * 800 / max(1, len(main) - 1), 205)
                 for i, s in enumerate(main)}
    # Place lower stages between their main-row neighbours. Reserve horizontal
    # slots for multiple lower stages, including chains of returned stages.
    lower_x = []
    for stage in below:
        neighbours = [positions[k][0] for p in paths
                      if stage["key"] in (p["from"], p["to"])
                      for k in (p["from"], p["to"]) if k in positions]
        lower_x.append(sum(neighbours) / len(neighbours) if neighbours else 500)
    if len(below) > 1:
        centre = sum(lower_x) / len(lower_x)
        spacing = min(240, 800 / (len(below) - 1))
        start = max(100, min(900 - spacing * (len(below) - 1),
                             centre - spacing * (len(below) - 1) / 2))
        lower_x = [start + i * spacing for i in range(len(below))]
    positions.update({s["key"]: (x, 340) for s, x in zip(below, lower_x)})

    occupied, nodes, labels, bands, rows = [], [], [], [], []
    for stage in stages:
        x, y = positions[stage["key"]]
        lower = stage.get("row") == "below"
        node = (f'<rect class="flow-node st-{_e(stage["key"])}" x="{x - 11:g}" y="{310 if lower else 150}" '
                f'width="22" height="{60 if lower else 110}" rx="6"/>')
        for text, baseline, cls, font in (
            (str(stage["label"]), 392 if lower else 28, "flow-stage", 16),
            (f'{stage["count"]} {stage.get("note", "")}'.rstrip(),
             418 if lower else 54, "flow-note", 15),
        ):
            tx, ty = _place(text, x, baseline, font, occupied)
            node += _text(text, tx, ty, cls, font)
        nodes.append(_link(node, stage.get("href")))

    maximum = max(p.get("count", 0) for p in paths)
    for p in paths:
        kind, count = p.get("kind", "normal"), p.get("count", 0)
        if kind not in _KINDS:
            kind = "normal"
        x0, y0 = positions[p["from"]]
        x1, y1 = positions[p["to"]]
        direction = 1 if x1 >= x0 else -1
        x0, x1 = x0 + direction * 11, x1 - direction * 11
        mid = (x0 + x1) / 2
        if kind == "urgent":
            y0 = y1 = 175
            c0 = c1 = 65
        elif kind in ("returned", "second_return"):
            y0 = 260 if y0 == 205 else y0
            y1 = 260 if y1 == 205 else y1
            c0 = c1 = 360
        else:
            c0, c1 = y0, y1
        thickness = max(4, 110 * max(0, count) / maximum)
        half = thickness / 2
        d = (f'M {x0:g} {y0-half:g} '
             f'C {mid:g} {c0-half:g} {mid:g} {c1-half:g} {x1:g} {y1-half:g} '
             f'L {x1:g} {y1+half:g} '
             f'C {mid:g} {c1+half:g} {mid:g} {c0+half:g} {x0:g} {y0+half:g} Z')
        source, target = by_key[p["from"]]["label"], by_key[p["to"]]["label"]
        description = f'{source} to {target}, {_KINDS[kind].lower()}: {count} cases'
        focus = '' if p.get("href") else ' tabindex="0"'  # a linked band takes focus through its link: one tab stop
        band = (f'<path class="band {kind}" d="{d}" data-thickness="{thickness:g}"'
                f'{focus}><title>{_e(description)}</title></path>')
        bands.append(_link(band, p.get("href")))
        text = str(count) + (" " + kind.replace("_", " ") if kind != "normal" else "")
        # Cubic midpoint, with a small baseline adjustment to centre the text.
        desired_y = (y0 + 3*c0 + 3*c1 + y1) / 8 + 7
        lx, ly = _place(text, mid, desired_y, 15, occupied)
        label = ""
        if (lx, ly) != (mid, desired_y):
            label += (f'<line class="flow-leader" x1="{mid:g}" y1="{desired_y-7:g}" '
                      f'x2="{lx:g}" y2="{ly-9:g}"/>')
        left, top, right, bottom = _box(text, lx, ly, 15)
        label += (f'<rect class="band-count-bg" x="{left-4:g}" y="{top-3:g}" '
                  f'width="{right-left+8:g}" height="{bottom-top+6:g}" rx="5"/>')
        label += _text(text, lx, ly, "band-count", 15)
        labels.append(_link(label, p.get("href")))
        rows.append((source, target, _KINDS[kind], count))

    height = max(440 if below else 380, max(box[3] for box in occupied) + 12)
    aria = ". ".join(str(v) for v in (title, summary) if v) or "Case flow"
    legend = ''.join(f'<li class="flow-legend-item {kind}">{words}</li>'
                     for kind, words in _KINDS.items()
                     if kind != "second_return" or any(p.get("kind") == kind for p in paths))
    headings = ''.join(f'<th scope="col">{v}</th>' for v in ("From", "To", "Path", "Cases"))
    table = ''.join('<tr>' + ''.join(f'<td>{_e(v)}</td>' for v in row) + '</tr>' for row in rows)
    return Markup(
        f'<figure class="flow-fig"><svg class="chart-svg flow" viewBox="0 0 1000 {height:g}" '
        f'role="group" aria-label="{_e(aria)}">'  # group, not img: the stage links and bands inside take focus
        + ''.join(bands + nodes + labels)
        + f'</svg><ul class="flow-legend">{legend}</ul>'
        f'<table class="sr-only"><thead><tr>{headings}</tr></thead><tbody>{table}</tbody></table></figure>'
    )
