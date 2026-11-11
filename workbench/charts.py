"""Shared pieces for the server-drawn charts in fluid.py and flow.py. No script, no inline style: looks come from CSS classes.
An empty input gives <p class="empty">No data</p>, never an empty drawing."""
from markupsafe import Markup, escape

EMPTY = Markup('<p class="empty">No data</p>')
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _e(v) -> str:
    return str(escape(v))
