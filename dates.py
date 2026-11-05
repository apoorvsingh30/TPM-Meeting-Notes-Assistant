"""Turn phrases like "by Friday" or "next Tuesday" into real dates.

Everything is worked out from the meeting date, never from "today".

Rules (kept simple on purpose):
  - "Friday", "by Friday", "on Friday"  -> the next Friday AFTER the meeting day
                                           (if the meeting is on a Friday, a week later)
  - "this Friday"                       -> the Friday on/after the meeting day
  - "next Tuesday"                      -> the Tuesday of NEXT calendar week (Mon-Sun)
  - "tomorrow", "today", "tonight"      -> meeting date +1 / +0 / +0
  - "EOD", "end of day", "COB"          -> the meeting date
  - "end of week", "EOW"                -> the Friday of this week
  - "end of next week"                  -> the Friday of next week
  - "end of month", "EOM"               -> last day of the meeting's month
  - "in 3 days", "in 2 weeks", "within 5 business days"
  - "2026-11-12", "Nov 12", "12th November"  (no year -> the meeting's year,
                                              or next year if that date is long past)
Anything else (for example "next week" or "soon") is left unresolved on purpose.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Callable, List, Optional, Tuple

PREP = r"(?:(?P<prep>by|on|before|until|till|due(?:\s+(?:on|by))?|no\s+later\s+than)\s+)?"

_DAY_INDEX = {
    "monday": 0, "mon": 0, "tuesday": 1, "tues": 1, "tue": 1,
    "wednesday": 2, "wed": 2, "thursday": 3, "thurs": 3, "thur": 3, "thu": 3,
    "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
_FULL_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
_MONTH_RE = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_MONTH_NUM = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

# Priority when a phrase has several date hints: explicit dates beat weekdays/relative
# words, which beat a bare "EOD".
P_EOD, P_RELATIVE, P_ABSOLUTE = 0, 1, 2


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _friday_of_week(meeting: date, next_week: bool = False) -> date:
    friday = _monday_of(meeting) + timedelta(days=4)
    if next_week:
        return friday + timedelta(days=7)
    return friday if meeting <= friday else friday + timedelta(days=7)


def _add_months(d: date, months: int) -> date:
    index = d.year * 12 + (d.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def _month_end(meeting: date, next_month: bool = False) -> date:
    first = _add_months(meeting.replace(day=1), 1 if next_month else 0)
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def _build(year: Optional[int], month: int, day: int, meeting: date) -> Optional[date]:
    try:
        if year is not None:
            return date(year, month, day)
        candidate = date(meeting.year, month, day)
        if candidate < meeting - timedelta(days=30):  # "Jan 15" said in November
            candidate = date(meeting.year + 1, month, day)
        return candidate
    except ValueError:
        return None


# ---- handlers: each takes (match, meeting) and returns a date or None -------------

def _relative(m, meeting):
    word = re.sub(r"\s+", "", m.group("w").lower())
    return meeting + timedelta(days={"today": 0, "tonight": 0, "tomorrow": 1,
                                     "dayaftertomorrow": 2}[word])


def _eod(m, meeting):
    return meeting


def _end_of(m, meeting):
    short = (m.group("short") or "").lower()
    unit = short and ("week" if short == "eow" else "month") or m.group("unit").lower()
    nxt = (m.group("which") or "").strip().lower() == "next"
    return _friday_of_week(meeting, nxt) if unit == "week" else _month_end(meeting, nxt)


def _in_n(m, meeting):
    raw = m.group("n").lower()
    n = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
    unit = m.group("u").lower()
    if unit.startswith("week"):
        return meeting + timedelta(weeks=n)
    if unit.startswith(("business", "working")):
        d = meeting
        while n > 0:
            d += timedelta(days=1)
            if d.weekday() < 5:
                n -= 1
        return d
    return meeting + timedelta(days=n)


def _weekday(m, meeting):
    day = m.group("day").lower()
    mod = (m.group("mod") or "").lower()
    # Short forms like "sat"/"sun"/"wed" are only trusted with a hint word in front,
    # so "we sat down" is not read as Saturday.
    if day not in _FULL_DAYS and not (m.group("prep") or mod):
        return None
    target = _DAY_INDEX[day]
    if mod in ("next", "following"):
        return _monday_of(meeting) + timedelta(days=7 + target)
    delta = (target - meeting.weekday()) % 7
    if delta == 0 and mod != "this":
        delta = 7
    return meeting + timedelta(days=delta)


def _iso(m, meeting):
    return _build(int(m.group("y")), int(m.group("mo")), int(m.group("d")), meeting)


def _month_day(m, meeting):
    year = int(m.group("y")) if m.group("y") else None
    return _build(year, _MONTH_NUM[m.group("mon").lower()[:3]], int(m.group("d")), meeting)


_I = re.I
_PATTERNS: List[Tuple[re.Pattern, int, Callable]] = [
    (re.compile(PREP + r"\b(?P<w>day\s+after\s+tomorrow|tomorrow|today|tonight)\b", _I),
     P_RELATIVE, _relative),
    (re.compile(PREP + r"\b(?:eod|cob|end\s+of\s+(?:the\s+)?day|close\s+of\s+business)\b", _I),
     P_EOD, _eod),
    (re.compile(PREP + r"\b(?:(?P<short>eow|eom)|end\s+of\s+(?P<which>the\s+|this\s+|next\s+)?"
                r"(?P<unit>week|month))\b", _I), P_RELATIVE, _end_of),
    (re.compile(PREP + r"\b(?:in|within)\s+(?P<n>\d+|an?|one|two|three|four|five|six|seven|eight"
                r"|nine|ten)\s+(?P<u>business\s+days?|working\s+days?|days?|weeks?)\b", _I),
     P_RELATIVE, _in_n),
    (re.compile(PREP + r"(?:\b(?P<mod>next|this|coming|following)\s+)?\b(?P<day>monday|tuesday"
                r"|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(?:rs?)?|fri|sat"
                r"|sun)\b", _I), P_RELATIVE, _weekday),
    (re.compile(PREP + r"\b(?P<y>\d{4})-(?P<mo>\d{1,2})-(?P<d>\d{1,2})\b", _I),
     P_ABSOLUTE, _iso),
    (re.compile(PREP + r"\b(?P<mon>" + _MONTH_RE + r")\.?\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?"
                r"(?:,?\s+(?P<y>\d{4}))?\b", _I), P_ABSOLUTE, _month_day),
    (re.compile(PREP + r"\b(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<mon>" + _MONTH_RE
                + r")\b\.?(?:,?\s+(?P<y>\d{4}))?\b", _I), P_ABSOLUTE, _month_day),
]


def find_due(text: str, meeting: date) -> Tuple[Optional[date], str, str]:
    """Find a due date in ``text``.

    Returns (date or None, the words that were used, text with those words removed).
    """
    found = []
    for regex, priority, handler in _PATTERNS:
        for m in regex.finditer(text):
            d = handler(m, meeting)
            if d is not None:
                found.append((m.start(), m.end(), priority, d))

    # Keep the longest match when two overlap (e.g. "next Tuesday" vs "Tuesday").
    found.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    kept: list = []
    for c in found:
        if all(c[1] <= k[0] or c[0] >= k[1] for k in kept):
            kept.append(c)
    if not kept:
        return None, "", text

    kept.sort()
    best = max(kept, key=lambda c: c[2])  # first one wins a tie
    phrase = " ".join(text[s:e].strip() for s, e, _, _ in kept)
    cleaned = text
    for s, e, _, _ in sorted(kept, reverse=True):
        cleaned = cleaned[:s] + " " + cleaned[e:]
    return best[3], phrase, re.sub(r"\s+", " ", cleaned).strip()
