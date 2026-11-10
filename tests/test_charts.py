import re

import pytest
from markupsafe import Markup

from workbench import charts

GRID = [[(d + h) % 4 for h in range(11)] for d in range(7)]
EMPTY = [lambda: charts.bars([]), lambda: charts.columns([]), lambda: charts.heatmap([])]
FULL = [lambda **k: charts.bars([("<b>", 3), ("Two", 5)], highlight="Two", **k),
        lambda **k: charts.columns([("<b>", 3), ("Two", 5), ("Three", 4)], **k),
        lambda **k: charts.heatmap(GRID, **k)]


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


def test_bars_values_are_labelled_and_in_table():
    out = charts.bars([("One", 3), ("Two", 5)], title="t", summary="s")
    assert ">3<" in out and ">5<" in out and out.count("<td>5</td>") == 1


@pytest.mark.parametrize("make", [FULL[0], FULL[1]])
def test_labels_are_escaped(make):
    assert "&lt;b&gt;" in make(title="t", summary="s")
