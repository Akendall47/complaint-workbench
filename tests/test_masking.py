from hypothesis import HealthCheck, given, settings, strategies as st

from workbench.masking import mask


def test_spaced_card_masked(p):
    assert mask("card 4929 1234 5678 9012", {}, p) == "card [CARD]"


def test_dotted_sort_code(p):
    assert "[SORT CODE]" in mask("sort 12.34.56", {}, p)


def test_case_reference_kept(p):
    assert mask("see AB-2026-00417 and POL-4.2", {}, p) == "see AB-2026-00417 and POL-4.2"


def test_no_details_unchanged(p):
    assert mask("The app froze twice.", {}, p) == "The app froze twice."


def test_known_values_longest_first_case_insensitive(p):
    known = {"name": "Ann Smith", "address": "1 High Street, Leeds", "dob": "01/02/1980"}
    out = mask("ANN SMITH of 1 high street, leeds, born 01/02/1980. Ann called.", known, p)
    assert out == "[NAME] of [ADDRESS], born [DOB]. Ann called."


def test_other_tokens(p):
    out = mask("a@b.co 07700 900123 SW1A 1AA 12 34 56, acc 12345678", {}, p)
    assert out == "[EMAIL] [PHONE] [POSTCODE] [SORT CODE], acc [ACCOUNT]"


_words = st.text(alphabet="abcdefghij .,", max_size=20)


def _embed(prefix, secret, suffix):
    return f"{prefix} {secret} {suffix}"


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    _words, _words,
    st.one_of(
        st.text("0123456789", min_size=16, max_size=16),
        st.text("0123456789", min_size=8, max_size=8),
        st.builds("{:02d}-{:02d}-{:02d}".format, *[st.integers(0, 99)] * 3),
    ),
)
def test_secret_digits_never_survive(p, a, b, secret):
    out = mask(_embed(a, secret, b), {}, p)
    assert secret not in out
    assert secret.replace("-", "") not in out.replace("-", "")
