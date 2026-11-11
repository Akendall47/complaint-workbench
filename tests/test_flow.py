"""Contract and independent SVG geometry checks; no database required."""

from copy import deepcopy
from itertools import combinations
import re
from xml.etree import ElementTree as ET

import pytest
from markupsafe import Markup

from workbench.charts import EMPTY
from workbench.flow import case_flow


STAGES = [
    {"key": key, "label": label, "count": count, "note": note,
     "href": f"/queue?owner=all&stage={key}" if key != "accepted" else None,
     "row": row}
    for key, label, count, note, row in [
        ("new", "New", 384, "here now", "main"),
        ("in_review", "In review", 322, "here now", "main"),
        ("handed_over", "Handed over", 385, "here now", "main"),
        ("accepted", "Accepted", 316, "closed", "main"),
        ("returned", "Returned", 193, "here now", "below"),
    ]
]
PATHS = [
    {"from": a, "to": b, "kind": kind, "count": n, "href": None}
    for a, b, kind, n in [
        ("new", "in_review", "normal", 871),
        ("new", "in_review", "urgent", 345),
        ("in_review", "handed_over", "normal", 741),
        ("in_review", "handed_over", "urgent", 305),
        ("handed_over", "accepted", "normal", 274),
        ("handed_over", "returned", "returned", 345),
        ("returned", "in_review", "returned", 152),
    ]
]


def render(stages=STAGES, paths=PATHS):
    return ET.fromstring(str(case_flow(stages, paths, "Pipeline", "Case movements")))


def with_class(root, tag, cls):
    return [e for e in root.iter(tag) if cls in e.get("class", "").split()]


def test_empty():
    assert case_flow(STAGES, []) == EMPTY
    assert case_flow(STAGES, [dict(p, count=0) for p in PATHS]) == EMPTY
    assert case_flow([], PATHS) == EMPTY


def test_real_data_and_accessibility():
    output = case_flow(STAGES, PATHS, "Pipeline", "Case movements")
    assert isinstance(output, Markup)
    root = ET.fromstring(str(output))
    svg = root.find("svg")
    assert svg.get("role") == "img"
    assert svg.get("aria-label") == "Pipeline. Case movements"
    assert len(with_class(svg, "path", "band")) == 7
    assert len(with_class(svg, "rect", "flow-node")) == 5
    counts = with_class(svg, "text", "band-count")
    assert len(counts) == len(with_class(svg, "rect", "band-count-bg")) == 7
    assert [e.text for e in counts] == ["871", "345 urgent", "741", "305 urgent", "274", "345 returned", "152 returned"]
    for stage in STAGES:
        assert f'{stage["count"]} {stage["note"]}' in [e.text for e in svg.iter("text")]
    rows = root.findall(".//tbody/tr")
    assert len(rows) == 7
    assert [r[2].text for r in rows] == ["Normal path", "Urgent fast path", "Normal path", "Urgent fast path", "Normal path", "Returned for more work", "Returned for more work"]
    assert root.find("details/summary").text == "Show the numbers"
    assert root.find("details").get("open") is None
    assert all(p.find("title") is not None for p in with_class(svg, "path", "band"))
    assert "Returned a second time" not in str(output)
    assert 'style=' not in output and '<script' not in output


@pytest.mark.parametrize("scenario", ["real", "skewed", "second_return", "crowded"])
def test_no_overlapping_labels(scenario):
    stages, paths = deepcopy(STAGES), deepcopy(PATHS)
    if scenario == "skewed":
        for i, path in enumerate(paths):
            path["count"] = 5000 if i == 0 else 1 + i % 3
    if scenario == "second_return":
        stages.append(dict(key="team_lead", label="Team lead review", count=23,
                           note="here now", href=None, row="below"))
        paths.append(dict({"from": "returned", "to": "team_lead"},
                          kind="second_return", count=45, href=None))
    if scenario == "crowded":
        paths *= 4
    root = render(stages, paths)
    svg = root.find("svg")
    _, _, width, height = map(float, svg.get("viewBox").split())
    boxes = []
    for el in svg.iter("text"):
        text = ''.join(el.itertext())
        font = 16 if "flow-stage" in el.get("class", "").split() else 15
        assert float(el.get("font-size")) == font
        w, h = len(text) * .6 * font, 1.2 * font
        x, y = float(el.get("x")), float(el.get("y"))
        anchor = el.get("text-anchor", "start")
        left = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
        box = (left, y - h, left + w, y, text)
        assert 0 <= box[0] <= box[2] <= width, box
        assert 0 <= box[1] <= box[3] <= height, box
        boxes.append(box)
    for a, b in combinations(boxes, 2):
        assert (a[2] + 6 <= b[0] + .001 or b[2] + 6 <= a[0] + .001
                or a[3] + 6 <= b[1] + .001 or b[3] + 6 <= a[1] + .001), (a, b)
    if scenario == "second_return":
        assert "Returned a second time" in ''.join(root.itertext())
        assert len(with_class(svg, "rect", "flow-node")) == 6
    if scenario == "crowded":
        assert with_class(svg, "line", "flow-leader")


def test_thickness_geometry():
    paths = [dict(PATHS[0], count=n) for n in (0, 1, 500, 1000, 5000)]
    bands = with_class(render(paths=paths), "path", "band")
    widths = []
    for band in bands:
        # Measure the two ribbon edges at their shared start x, independently
        # of the diagnostic data-thickness attribute.
        nums = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", band.get("d"))))
        widths.append(nums[-1] - nums[1])
        assert band.get("d").count("C") == 2
        assert band.get("d").endswith(" Z")
    assert widths == sorted(widths)
    assert min(widths) >= 4
    assert widths[-1] == 110
    assert widths[2] < widths[3] < widths[4]


def test_escaping_and_links():
    stages, paths = deepcopy(STAGES), deepcopy(PATHS)
    stages[0]["label"] = '<script>alert("x")</script>'
    href = '/queue?x="quoted"&y=<tag>'
    stages[0]["href"] = paths[0]["href"] = href
    output = str(case_flow(stages, paths, '<script>', '"summary"'))
    assert '<script>' not in output
    assert '&lt;script&gt;' in output and '&#34;' in output
    root = ET.fromstring(output)
    assert root.find("svg").get("aria-label") == '<script>. "summary"'
    assert sum(a.get("href") == href for a in root.iter("a")) == 3
    assert stages[0]["label"] in [e.text for e in root.iter("text")]


def test_unknown_stage_and_determinism():
    bad = dict(PATHS[0], **{"from": "missing"})
    assert case_flow(STAGES, PATHS + [bad]) == case_flow(STAGES, PATHS)
    assert case_flow(STAGES, [bad]) == EMPTY
    assert case_flow(STAGES, PATHS) == case_flow(STAGES, PATHS)
