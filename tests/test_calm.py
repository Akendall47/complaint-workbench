"""Calm pass: the deadline strip and the Queue owner column."""
import re

from tests.test_views_reference import as_role


def test_strip_only_on_overview_and_queue(client):
    as_role(client, "team_lead", "T1")
    for path in ("/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"):
        assert 'class="strip"' not in client.get(path).text, path
    for path in ("/", "/queue"):
        assert 'class="strip"' in client.get(path).text, path


def test_queue_owner_column_follows_the_tab_and_shows_names(client):
    assert '<th scope="col">Owner</th>' not in client.get("/queue?owner=me").text
    html = client.get("/queue?owner=all").text
    assert '<th scope="col">Owner</th>' in html and not re.search(r"<td>[HST]\d</td>", html)
