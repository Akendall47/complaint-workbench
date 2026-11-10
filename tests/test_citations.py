from hypothesis import given, strategies as st

from workbench.citations import quote_in_source


def test_short_quote_fails():
    assert not quote_in_source("the", "the customer called")


def test_whitespace_and_case():
    assert quote_in_source("Called  on\nMonday morning", "she called on monday morning.")


def test_absent_quote_fails():
    assert not quote_in_source("refund was promised in writing", "no refund discussed")


@given(st.text("abcdefghijklm \n", max_size=200), st.text("nopqrstuvwxyz", min_size=12, max_size=30))
def test_disjoint_alphabet_never_matches(source, quote):
    assert not quote_in_source(quote, source)


def test_curly_apostrophe_matches_straight():
    assert quote_in_source("the customer’s card was lost", "The customer's card was lost.")
    assert quote_in_source("the customer's card was lost", "The customer’s card was lost.")


def test_length_boundary():
    src = "abcdefghijkl and more"
    assert not quote_in_source("abcdefghijk", src)  # 11
    assert quote_in_source("abcdefghijkl", src)  # 12
