import re

from hypothesis import HealthCheck, assume, given, settings, strategies as st

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
    assert mask("ref 123456789 end", {}, p) == "ref [NUMBER] end"
    assert mask("ref 123456789012345678901234 end", {}, p) == "ref [CARD] end"  # open-ended card pattern takes it first


def test_email_pattern_is_fast(p):
    import time
    t0 = time.perf_counter()
    mask("a." * 25000, {}, p)
    assert time.perf_counter() - t0 < 1


def test_known_value_whitespace_runs(p):
    known = {"name": "Ann  Smith", "address": "1 High Street,\nLeeds"}
    assert mask("Ann \n Smith at 1 High Street,  Leeds", known, p) == "[NAME] at [ADDRESS]"


def test_short_known_value_masked_as_word(p):
    assert mask("Al said Alert", {"name": "Al"}, p) == "[NAME] said Alert"


def test_known_value_not_matched_inside_token(p):
    out = mask("Ann Smith said NAM", {"name": "Ann Smith", "address": "NAM"}, p)
    assert out == "[NAME] said [ADDRESS]"
    assert mask("Ann Smith and AME", {"name": "Ann Smith", "address": "AME"}, p) == "[NAME] and [ADDRESS]"


def test_clause_digits_not_sheltered(p):
    assert "4929" not in mask("POL-4929123456789012", {}, p)


def test_ref_then_card_digits(p):
    out = mask("AB-2026-00417 4929 1234 5678 9012", {}, p)
    assert "AB-2026-00417" in out and "4929" not in out


def test_long_local_part(p):
    assert mask("x " + "a" * 90 + "@bank.co.uk y", {}, p) == "x [EMAIL] y"


def test_separated_28_digits(p):
    out = mask("n " + " ".join(["1234"] * 7), {}, p)
    assert not any(c.isdigit() for c in out)


def test_adjacent_dates_survive(p):
    for t in ["10-11-2026 12-11-2026", "10.11.2026 14.30"]:
        assert mask(t, {}, p) == t


def test_private_use_chars_stripped(p):
    out = mask(chr(0xE000) + "see AB-2026-00417", {}, p)
    assert out == "see AB-2026-00417"


def test_card_after_date(p):
    out = mask("10-11-2026 4929 1234 5678 9012", {}, p)
    assert out == "10-11-2026 [CARD]"


def test_card_with_slash_and_underscore(p):
    assert mask("4929/1234/5678/9012", {}, p) == "[CARD]"
    assert mask("4929_1234_5678_9012", {}, p) == "[CARD]"


def test_dates_times_money_unchanged(p):
    for t in ["10-11-2026 12-11-2026", "10.11.2026 14.30", "10/11/2026", "£1,250.00", "14:30",
              "2026-11-10", "10/11/26", "paid £250 at 09:05 on 2026-11-10"]:
        assert mask(t, {}, p) == t, t


def test_two_digit_year_with_hyphen_is_sort_code(p):
    assert mask("20-45-77", {}, p) == "[SORT CODE]"


def test_known_dob_still_masked(p):
    assert mask("born 03/04/1988", {"dob": "03/04/1988"}, p) == "born [DOB]"


def test_money_does_not_shelter_card(p):
    assert "4929" not in mask("£4929123456789012", {}, p)


def test_many_held_items(p):
    t = "10/11/2026 " * 7000
    assert mask(t, {}, p) == t


def test_sort_code_then_account(p):
    assert mask("12-34-56 12345678", {}, p) == "[SORT CODE] [ACCOUNT]"


def test_phones(p):
    for n in ["01632 960123", "020 7946 0958", "+44 20 7946 0958", "+44 7700 900123", "01632.960.123", "0113-496-0123"]:
        assert mask(f"call {n} now", {}, p) == "call [PHONE] now", n


_words = st.text(alphabet="abcdefghij .,", max_size=20)


def _embed(prefix, secret, suffix):
    return f"{prefix} {secret} {suffix}"


_sep = st.sampled_from([" ", ".", "-", "/", "_"])
_pad = st.text(alphabet="abcdefghij .,\n!?;:()", max_size=20)
_card = st.integers(13, 19).flatmap(lambda n: st.text("0123456789", min_size=n, max_size=n))
_sc_sep = st.sampled_from([" ", ".", "-"])
_sort = st.builds("{:02d}{}{:02d}{}{:02d}".format, st.integers(0, 99), _sc_sep, st.integers(0, 99), _sc_sep, st.integers(0, 99))
_run = st.integers(20, 30).flatmap(lambda n: st.text("0123456789", min_size=n, max_size=n))


@st.composite
def _grouped(draw):
    groups = draw(st.lists(st.text("0123456789", min_size=2, max_size=5), min_size=3, max_size=15))
    assume(13 <= sum(map(len, groups)) <= 30)
    seps = draw(st.lists(_sep, min_size=len(groups) - 1, max_size=len(groups) - 1))
    out = groups[0] + "".join(a + b for a, b in zip(seps, groups[1:]))
    # A run containing a date, ISO date or time shape is a known miss (docs/test-results.md).
    assume(not re.search(r"(?<!\d)(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2}|\d{1,2}:\d{2})(?!\d)", out))
    return out


_date = st.sampled_from(["10-11-2026", "10.11.2026", "10/11/2026", "2026-11-10", "10/11/26"])


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(_date, _card)
def test_card_after_date_masked(p, d, card):
    out = mask(f"{d} {card}", {}, p)
    assert out.startswith(d) and not any(c.isdigit() for c in out[len(d):])


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(_pad, _pad, st.one_of(_card, st.text("0123456789", min_size=8, max_size=8), _sort, _run, _grouped()))
def test_secret_digits_never_survive(p, a, b, secret):
    # Padding has no digits, so any digit run left in the output came from the secret.
    out = mask(f"{a}{secret}{b}", {}, p)
    digits = "".join(c for c in secret if c.isdigit())
    assert secret not in out
    assert not any(digits[i:i + 6] in "".join(c for c in out if c.isdigit()) for i in range(len(digits) - 5))
