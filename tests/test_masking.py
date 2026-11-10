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


def test_ref_kept_next_to_card(p):
    assert mask("AB-2026-00417 4929 1234 5678 9012", {}, p) == "AB-2026-00417 [CARD]"


def test_dates_and_money_survive(p):
    t = "On 10/11/2026 I paid £1,250.00 under POL-4.2."
    assert mask(t, {}, p) == t


def test_long_digit_run(p):
    assert mask("ref 123456789012345678901234 end", {}, p) == "ref [NUMBER] end"


def test_email_pattern_is_fast(p):
    import time
    t0 = time.perf_counter()
    mask("a." * 25000, {}, p)
    assert time.perf_counter() - t0 < 1


def test_known_value_whitespace_runs(p):
    known = {"name": "Ann  Smith", "address": "1 High Street,\nLeeds"}
    assert mask("Ann \n Smith at 1 High Street,  Leeds", known, p) == "[NAME] at [ADDRESS]"


def test_short_known_value_skipped(p):
    assert mask("an ox", {"name": "an"}, p) == "an ox"


def test_sort_code_then_account(p):
    assert mask("12-34-56 12345678", {}, p) == "[SORT CODE] [ACCOUNT]"


def test_phones(p):
    for n in ["01632 960123", "020 7946 0958", "+44 20 7946 0958", "+44 7700 900123", "01632.960.123", "0113-496-0123"]:
        assert mask(f"call {n} now", {}, p) == "call [PHONE] now", n


_words = st.text(alphabet="abcdefghij .,", max_size=20)


def _embed(prefix, secret, suffix):
    return f"{prefix} {secret} {suffix}"


_sep = st.sampled_from([" ", ".", "-"])
_pad = st.text(alphabet="abcdefghij .,\n!?;:()", max_size=20)
_card = st.integers(13, 19).flatmap(lambda n: st.text("0123456789", min_size=n, max_size=n))
_sort = st.builds("{}{}{}{}{}".format, st.integers(10, 99), _sep, st.integers(10, 99), _sep, st.integers(10, 99))
_run = st.integers(20, 30).flatmap(lambda n: st.text("0123456789", min_size=n, max_size=n))


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(_pad, _pad, st.one_of(_card, st.text("0123456789", min_size=8, max_size=8), _sort, _run))
def test_secret_digits_never_survive(p, a, b, secret):
    # Padding has no digits, so any digit run left in the output came from the secret.
    out = mask(f"{a}{secret}{b}", {}, p)
    digits = "".join(c for c in secret if c.isdigit())
    assert secret not in out
    assert not any(digits[i:i + 6] in "".join(c for c in out if c.isdigit()) for i in range(len(digits) - 5))
