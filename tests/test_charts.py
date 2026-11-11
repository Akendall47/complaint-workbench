"""The fluid charts: empty input is a paragraph, text is escaped, bars scale to the largest value, and nothing uses inline style."""
import re

import pytest
from markupsafe import Markup

from workbench import fluid

GRID = [[(d + h) % 4 for h in range(11)] for d in range(7)]
MAKERS = {
    "track": lambda items: fluid.track(items),
    "cols": lambda items: fluid.cols(items, "label"),
    "area": lambda items: fluid.area(items, "label"),
}


@pytest.mark.parametrize("name", MAKERS)
def test_empty_input_is_a_paragraph_not_a_drawing(name):
    assert MAKERS[name]([]) == Markup('<p class="empty">No data</p>')


def test_empty_heatmap_and_map_are_paragraphs():
    assert fluid.heat([[0] * 11] * 7, range(8, 19), "x") == Markup('<p class="empty">No data</p>')
    assert fluid.band_map([]) == Markup('<p class="empty">No data</p>')


@pytest.mark.parametrize("name", MAKERS)
def test_labels_are_escaped_and_no_inline_style(name):
    html = str(MAKERS[name]([("<script>", 3), ("Two", 5)]))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "style=" not in html


def test_track_bars_scale_to_the_largest_value():
    widths = re.findall(r'class="tk-fill[^"]*" width="([\d.]+)%"', str(fluid.track([("a", 5), ("b", 10)])))
    assert widths == ["50", "100"]


def test_heatmap_has_a_cell_per_hour_and_the_counts_in_a_table():
    html = str(fluid.heat(GRID, range(8, 19), "When complaints arrive"))
    assert html.count('class="hc l') == 7 * 11 + 5  # cells plus the five legend swatches
    assert 'role="img" aria-label="When complaints arrive"' in html and '<table class="sr-only">' in html


def test_band_map_links_every_band_and_gives_each_node_a_label():
    html = str(fluid.band_map([("Fraud claims", "Payment scam", 7), ("Bereavement", "Service", 2)], href=lambda d, t: f"/queue?type={t}"))
    assert html.count('<path class="mband"') == 2 and html.count('<a href="/queue?type=') == 2
    assert "Fraud claims" in html and "Payment scam" in html
