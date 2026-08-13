"""Deterministic money and date verification (SPEC section 4).

The model never decides whether two numbers or two dates match. It cannot be
audited when it does, it is not reliably correct at it, and a compliance finding
that turns on whether $4,500.00 equals "forty five hundred dollars" has to be
defensible by inspection rather than by trust.

So this module canonicalises first and compares in code afterwards. Everything
here is pure: no model, no network, no clock except the call date passed in
explicitly. That is what makes the test suite meaningful and what lets it stay
independent of the judge, as SPEC section 4 requires.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum


class CheckResult(str, Enum):
    """Outcome of one deterministic comparison."""

    MATCH = "match"
    MISMATCH = "mismatch"
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class Check:
    """One deterministic comparison, with both sides recorded.

    Both the parsed and the expected value are kept even on a mismatch, because
    the check.deterministic span in SPEC section 7 has to show what was compared,
    not merely that the comparison failed.
    """

    result: CheckResult
    value_parsed: str | None
    expected_value: str | None
    detail: str = ""

    def to_dict(self) -> dict[str, str | None]:
        return {
            "result": self.result.value,
            "value_parsed": self.value_parsed,
            "expected_value": self.expected_value,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000}

_CENTS_WORDS = {"cent", "cents"}
_CURRENCY_WORDS = {"dollar", "dollars", "buck", "bucks"}
_FILLER_WORDS = {"and", "a", "the"}

_NUMERIC_RE = re.compile(r"-?\$?\s*\d[\d,]*(?:\.\d+)?")
_WORD_RE = re.compile(r"[a-z]+")


class NumberParseError(ValueError):
    """Raised when a string cannot be read as a single number."""


def normalize_number(text: str) -> Decimal:
    """Parse a spoken or written number into an exact Decimal.

    Handles "$35.00", "35", "thirty-five", "four thousand five hundred",
    "twelve dollars and fifty cents". Decimal rather than float because money
    comparisons must be exact: 0.1 + 0.2 != 0.3 in binary floating point, and a
    compliance finding is not the place to discover that.
    """
    cleaned = text.strip().lower().replace("–", "-").replace("—", "-")
    if not cleaned:
        raise NumberParseError("empty string")

    digits = _NUMERIC_RE.findall(cleaned)
    words = [w for w in _WORD_RE.findall(cleaned) if w not in _FILLER_WORDS]

    has_word_number = any(
        w in _UNITS or w in _TENS or w in _SCALES for w in words
    )

    if digits and not has_word_number:
        return _parse_digit_form(cleaned, digits, words)
    if has_word_number:
        return _parse_word_form(words)
    raise NumberParseError(f"no number found in {text!r}")


def _parse_digit_form(cleaned: str, digits: list[str], words: list[str]) -> Decimal:
    """Parse digit forms, including a trailing spoken cents amount."""
    primary = _to_decimal(digits[0])
    # "35 dollars and 50 cents" -> two digit groups, the second being cents.
    if len(digits) > 1 and any(w in _CENTS_WORDS for w in words):
        cents = _to_decimal(digits[1])
        if cents >= 100:
            raise NumberParseError(f"cents value out of range in {cleaned!r}")
        primary = primary + (cents / Decimal(100))
    return primary


def _to_decimal(token: str) -> Decimal:
    stripped = token.replace("$", "").replace(",", "").strip()
    try:
        return Decimal(stripped)
    except InvalidOperation as exc:
        raise NumberParseError(f"cannot parse {token!r} as a number") from exc


def _parse_word_form(words: list[str]) -> Decimal:
    """Parse an English number phrase, with an optional cents tail.

    Split on the currency word: "twelve dollars and fifty cents" divides into
    ["twelve"] and ["fifty"]. With no currency word the whole phrase is one
    number, so "thirty-five" is 35 rather than 35 dollars 0 cents.
    """
    currency_index = next(
        (i for i, word in enumerate(words) if word in _CURRENCY_WORDS), None
    )
    if currency_index is None:
        bare = [w for w in words if w not in _CENTS_WORDS]
        value = Decimal(_words_to_int(bare))
        # "ten cents" with no dollar part is a cents amount, not ten dollars.
        # Reading it as 10 would overstate an amount by a factor of a hundred,
        # which is precisely the class of error this module exists to prevent.
        if any(w in _CENTS_WORDS for w in words):
            return value / Decimal(100)
        return value

    dollar_words = words[:currency_index]
    cent_words = [w for w in words[currency_index + 1 :] if w not in _CENTS_WORDS]

    dollars = _words_to_int(dollar_words)
    cents = _words_to_int(cent_words) if cent_words else 0
    if cents >= 100:
        raise NumberParseError(f"cents value out of range: {cents}")
    return Decimal(dollars) + (Decimal(cents) / Decimal(100))


def _words_to_int(words: list[str]) -> int:
    """Accumulate an English number phrase into an integer.

    Standard two-accumulator approach: `current` builds the value under the
    active scale word, `total` banks it when a scale of thousand or more closes.
    """
    if not words:
        return 0
    total = 0
    current = 0
    seen = False

    for word in words:
        for part in word.split("-"):
            if not part:
                continue
            if part in _UNITS:
                current += _UNITS[part]
                seen = True
            elif part in _TENS:
                current += _TENS[part]
                seen = True
            elif part in _SCALES:
                scale = _SCALES[part]
                if current == 0:
                    current = 1
                if scale == 100:
                    current *= scale
                else:
                    total += current * scale
                    current = 0
                seen = True
            else:
                raise NumberParseError(f"unrecognised number word {part!r}")
    if not seen:
        raise NumberParseError("no number words found")
    return total + current


def check_amount(spoken: str, expected: Decimal | str) -> Check:
    """Compare a spoken amount against the expected value, in code."""
    try:
        expected_value = (
            expected if isinstance(expected, Decimal) else normalize_number(str(expected))
        )
    except NumberParseError as exc:
        return Check(CheckResult.UNPARSEABLE, None, str(expected), f"expected side: {exc}")

    try:
        parsed = normalize_number(spoken)
    except NumberParseError as exc:
        return Check(CheckResult.UNPARSEABLE, None, str(expected_value), str(exc))

    result = CheckResult.MATCH if parsed == expected_value else CheckResult.MISMATCH
    return Check(result, str(parsed), str(expected_value))


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_MONTHS = {name.lower(): num for num, name in enumerate(calendar.month_name) if name}
_MONTHS.update(
    {name.lower(): num for num, name in enumerate(calendar.month_abbr) if name}
)
# calendar supplies "sep" but people say and write "sept".
_MONTHS["sept"] = 9

_ORDINAL_SUFFIX_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b")
_ISO_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_US_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
_MONTH_DAY_RE = re.compile(r"\b([a-z]+)\s+(\d{1,2})\b")
_DAY_MONTH_RE = re.compile(r"\b(\d{1,2})\s+(?:of\s+)?([a-z]+)\b")
_IN_N_DAYS_RE = re.compile(r"\bin\s+([a-z0-9\- ]+?)\s+(day|business day|week|month)s?\b")
_WITHIN_N_RE = re.compile(r"\bwithin\s+([a-z0-9\- ]+?)\s+(day|business day|week|month)s?\b")


class DateParseError(ValueError):
    """Raised when a string cannot be read as a single date."""


def normalize_date(text: str, call_date: date) -> date:
    """Resolve a spoken or written date against the date of the call.

    `call_date` is required rather than defaulting to today. Relative phrases
    like "next Tuesday" only mean something relative to when the call happened,
    and a finding regenerated six months later must resolve to the same date it
    did originally. Reading the system clock here would silently break
    reproducibility, which SPEC section 7 defines as the property that stored
    inputs regenerate the same verdict.
    """
    cleaned = _ORDINAL_SUFFIX_RE.sub(r"\1", text.strip().lower())
    if not cleaned:
        raise DateParseError("empty string")

    if "today" in cleaned:
        return call_date
    if "tomorrow" in cleaned:
        return call_date + timedelta(days=1)
    if "yesterday" in cleaned:
        return call_date - timedelta(days=1)

    iso = _ISO_RE.search(cleaned)
    if iso:
        return _safe_date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))

    slash = _US_SLASH_RE.search(cleaned)
    if slash:
        month, day = int(slash.group(1)), int(slash.group(2))
        year = _resolve_year(slash.group(3), call_date)
        return _safe_date(year, month, day)

    offset = _relative_offset(cleaned)
    if offset is not None:
        return offset(call_date)

    weekday = _weekday_target(cleaned, call_date)
    if weekday is not None:
        return weekday

    month_day = _MONTH_DAY_RE.search(cleaned)
    if month_day and month_day.group(1) in _MONTHS:
        month = _MONTHS[month_day.group(1)]
        return _forward_looking(call_date, month, int(month_day.group(2)))

    day_month = _DAY_MONTH_RE.search(cleaned)
    if day_month and day_month.group(2) in _MONTHS:
        month = _MONTHS[day_month.group(2)]
        return _forward_looking(call_date, month, int(day_month.group(1)))

    raise DateParseError(f"cannot resolve {text!r} to a date")


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise DateParseError(f"invalid date {year}-{month}-{day}") from exc


def _resolve_year(raw: str | None, call_date: date) -> int:
    if raw is None:
        return call_date.year
    value = int(raw)
    if value < 100:
        # Two-digit years land in the current century. Collection calls do not
        # discuss dates a century out, so this is unambiguous in practice.
        return (call_date.year // 100) * 100 + value
    return value


def _relative_offset(cleaned: str):  # type: ignore[no-untyped-def]
    """Resolve "in 30 days", "within two weeks", "in a month"."""
    match = _IN_N_DAYS_RE.search(cleaned) or _WITHIN_N_RE.search(cleaned)
    if not match:
        return None
    quantity_text, unit = match.group(1).strip(), match.group(2)
    try:
        quantity = int(normalize_number(quantity_text))
    except NumberParseError:
        return None

    if unit == "business day":
        return lambda anchor: _add_business_days(anchor, quantity)
    if unit == "day":
        return lambda anchor: anchor + timedelta(days=quantity)
    if unit == "week":
        return lambda anchor: anchor + timedelta(weeks=quantity)
    return lambda anchor: _add_months(anchor, quantity)


def _add_business_days(anchor: date, count: int) -> date:
    """Advance by business days, skipping weekends.

    Federal holidays are not modelled. Regulation F counts business days for
    several obligations, so this is a known simplification rather than an
    oversight, and it is listed in the report's limitations.
    """
    current = anchor
    remaining = count
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _add_months(anchor: date, count: int) -> date:
    month_index = anchor.month - 1 + count
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _weekday_target(cleaned: str, call_date: date) -> date | None:
    """Resolve "next Tuesday" and "this Friday" to the next such weekday.

    "next Tuesday" is genuinely ambiguous in English: said on a Wednesday it can
    mean six days out or thirteen. This resolves it as the next occurrence
    strictly after the call date, so "this" and "next" behave identically, and
    the ambiguity is named in the report's limitations rather than settled
    silently. The alternative reading would misdate a payment commitment by a
    week, which for a promise-to-pay is a material error in either direction.

    A production deployment should have the extractor capture the surrounding
    phrasing so an ambiguous weekday reference routes to abstention instead of
    being resolved by a coin flip. That is deferred, not solved.
    """
    for name, index in _WEEKDAYS.items():
        if name not in cleaned:
            continue
        ahead = (index - call_date.weekday()) % 7
        if ahead == 0:
            ahead = 7
        return call_date + timedelta(days=ahead)
    return None


def _forward_looking(call_date: date, month: int, day: int) -> date:
    """Pick the year for a bare month and day.

    A bare "March 3" on a call in November means the coming March. Payment
    commitments point forward, so resolving backwards would misdate every
    year-boundary promise.
    """
    candidate = _safe_date(call_date.year, month, day)
    if candidate < call_date:
        candidate = _safe_date(call_date.year + 1, month, day)
    return candidate


def check_date(spoken: str, expected: date | str, call_date: date) -> Check:
    """Compare a spoken date against the expected date, in code."""
    try:
        expected_value = (
            expected
            if isinstance(expected, date)
            else normalize_date(str(expected), call_date)
        )
    except DateParseError as exc:
        return Check(CheckResult.UNPARSEABLE, None, str(expected), f"expected side: {exc}")

    try:
        parsed = normalize_date(spoken, call_date)
    except DateParseError as exc:
        return Check(CheckResult.UNPARSEABLE, None, expected_value.isoformat(), str(exc))

    result = CheckResult.MATCH if parsed == expected_value else CheckResult.MISMATCH
    return Check(result, parsed.isoformat(), expected_value.isoformat())
