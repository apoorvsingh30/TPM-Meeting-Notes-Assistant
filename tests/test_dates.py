from datetime import date

import pytest

from dates import find_due

THU = date(2026, 11, 5)  # a Thursday
MON = date(2026, 11, 2)  # a Monday
FRI = date(2026, 11, 6)  # a Friday


@pytest.mark.parametrize("text, meeting, expected", [
    ("send it by Friday", THU, "2026-11-06"),
    ("send it by Friday", FRI, "2026-11-13"),            # same weekday -> a week later
    ("by Thursday", THU, "2026-11-12"),
    ("on this Friday", THU, "2026-11-06"),
    ("this Friday", FRI, "2026-11-06"),
    ("next Tuesday", THU, "2026-11-10"),
    ("next Tuesday", MON, "2026-11-10"),                 # next calendar week
    ("next Friday", THU, "2026-11-13"),
    ("by Mon", THU, "2026-11-09"),
    ("tomorrow", THU, "2026-11-06"),
    ("today", THU, "2026-11-05"),
    ("the day after tomorrow", THU, "2026-11-07"),
    ("by EOD", THU, "2026-11-05"),
    ("EOD Friday", THU, "2026-11-06"),
    ("by end of week", THU, "2026-11-06"),
    ("by end of week", date(2026, 11, 7), "2026-11-13"),  # said on a Saturday
    ("by end of next week", THU, "2026-11-13"),
    ("EOM", THU, "2026-11-30"),
    ("end of the month", date(2026, 12, 10), "2026-12-31"),
    ("end of next month", date(2026, 12, 10), "2027-01-31"),
    ("in 3 days", THU, "2026-11-08"),
    ("in two weeks", THU, "2026-11-19"),
    ("within 3 business days", THU, "2026-11-10"),
    ("by 2026-11-12", THU, "2026-11-12"),
    ("by Nov 12", THU, "2026-11-12"),
    ("on 12th December", THU, "2026-12-12"),
    ("Jan 15", THU, "2027-01-15"),                       # January has passed -> next year
    ("Friday, Nov 13", THU, "2026-11-13"),               # explicit date beats weekday
])
def test_resolves_real_date(text, meeting, expected):
    due, phrase, _ = find_due(text, meeting)
    assert due is not None and due.isoformat() == expected
    assert phrase


@pytest.mark.parametrize("text", [
    "we sat down and talked", "next week", "soon", "no date here", "Feb 31",
])
def test_leaves_unclear_phrases_alone(text):
    assert find_due(text, THU)[0] is None


def test_removes_the_date_words_from_the_text():
    _, phrase, rest = find_due("fix the signup bug before next Tuesday", THU)
    assert rest == "fix the signup bug"
    assert phrase == "before next Tuesday"
