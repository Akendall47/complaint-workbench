import re

import pytest
from markupsafe import Markup

from workbench import charts

GRID = [[(d + h) % 4 for h in range(11)] for d in range(7)]
EMPTY = [lambda: charts.bars([]), lambda: charts.columns([]), lambda: charts.heatmap([]),
         lambda: charts.band_flow([], [], [])]
FULL = [lambda **k: charts.bars([("<b>", 3), ("Two", 5)], highlight="Two", **k),
        lambda **k: charts.columns([("<b>", 3), ("Two", 5), ("Three", 4)], **k),
        lambda **k: charts.heatmap(GRID, **k),
        lambda **k: charts.band_flow(["<b>", "L2"], ["R1"], [("<b>", "R1", 7, "/queue?a=1"), ("L2", "R1", 1, "/queue?a=2")], **k)]


@pytest.mark.parametrize("make", EMPTY)
def test_empty_input_is_a_paragraph_not_an_svg(make):
    assert make() == Markup('<p class="empty">No data</p>')


@pytest.mark.parametrize("make", FULL)
def test_every_chart_has_text_alternative_and_is_safe(make):
    out = make(title="A title", summary="One plain sentence.")
    assert isinstance(out, Markup)
    assert 'role="img"' in out and 'aria-label="A title. One plain sentence."' in out
    assert "<script" not in out and "style=" not in out and "<b>" not in out
    assert "<details" in out and "<table" in out  # the numbers, reachable as a table


@pytest.mark.parametrize("make", FULL[:3])
def test_drawing_is_not_a_tab_stop(make):
    assert not re.search(r'href=|tabindex=', make(title="t", summary="s"))


def test_band_flow_min_width_titles_links_and_visible_counts():
    out = charts.band_flow(["A", "B"], ["X"], [("A", "X", 1000, "/q?1"), ("B", "X", 1, "/q?2")], title="t", summary="s")
    widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', out)]
    assert len(widths) == 2 and min(widths) >= 3
    assert out.count("<title>") >= 2 and out.count('<a href="/q?') == 2
    assert ">1000<" in out and ">1<" in out  # counts are drawn, not only in the table


def test_band_flow_marks_are_not_colour_only():
    out = charts.band_flow(["A"], ["X"], [("A", "X", 5, "/q")], marks=[("A", "X")], title="t", summary="s")
    assert 'class="band mark"' in out and "rising" in out


def test_bars_values_are_labelled_and_in_table():
    out = charts.bars([("One", 3), ("Two", 5)], title="t", summary="s")
    assert ">3<" in out and ">5<" in out and out.count("<td>5</td>") == 1


@pytest.mark.parametrize("make", [FULL[0], FULL[1], FULL[3]])
def test_labels_are_escaped(make):
    assert "&lt;b&gt;" in make(title="t", summary="s")
