from datetime import date
from pathlib import Path

import pytest

import extractor
from extractor import UNASSIGNED, extract, extract_rules, rows_from_ai_json

SAMPLE = (Path(__file__).parent.parent / "sample_notes.txt").read_text(encoding="utf-8")
MEETING = date(2026, 11, 2)  # the sample is a Monday meeting


def by_type(rows, kind):
    return [r for r in rows if r["type"] == kind]


def find(rows, start):
    return next(r for r in rows if r["text"].startswith(start))


def test_sample_notes_end_to_end():
    rows = extract_rules(SAMPLE, MEETING)
    assert [r["text"] for r in by_type(rows, "decision")] == [
        "We decided to push the public launch to Nov 24 instead of Nov 17",
        "Agreed to keep pricing as is for now",
    ]
    actions = by_type(rows, "action")
    assert len(actions) == 5
    deck = find(actions, "Send the updated launch deck")
    assert (deck["owner"], deck["due"]) == ("Priya", "2026-11-06")
    bug = find(actions, "Fix the signup bug")
    assert (bug["owner"], bug["due"], bug["text"]) == ("Sam", "2026-11-10", "Fix the signup bug")
    demo = find(actions, "Book the demo environment")
    assert (demo["owner"], demo["due"]) == ("Marco", "2026-11-06")
    legal = find(actions, "Confirm legal sign-off")
    assert (legal["owner"], legal["due"]) == ("Lena", "2026-11-12")
    docs = find(actions, "Update the help-centre")
    assert (docs["owner"], docs["due"]) == (UNASSIGNED, "")

    follow = by_type(rows, "follow_up")
    assert [(r["owner"], r["due"]) for r in follow] == [("Marco", "2026-11-03"), (UNASSIGNED, "")]
    assert len(by_type(rows, "question")) == 2
    assert len(by_type(rows, "risk")) == 2


@pytest.mark.parametrize("line", [
    "We need to hire a designer",
    "Someone should check the pricing page by Friday",
    "I will send the report",
    "The team will review the roadmap",
    "priya to send the deck",          # lowercase name: not trusted, so not used
    "Update to the docs is needed - need to do it",
])
def test_never_guesses_an_owner(line):
    rows = extract_rules(f"Action items\n- {line}", MEETING)
    assert rows and all(r["owner"] == UNASSIGNED for r in rows)


@pytest.mark.parametrize("line, owner", [
    ("Priya will email the client", "Priya"),
    ("Send the invoice - Marco", "Marco"),
    ("Owner: Dana - draft the memo", "Dana"),
    ("Draft the memo, assigned to Dana", "Dana"),
    ("Draft the memo @dana", "dana"),
    ("Sam and Lena to run the demo", "Sam and Lena"),
    ("Review the Q4 numbers (Priya, Fri)", "Priya"),
])
def test_finds_named_owners(line, owner):
    row = extract_rules(f"Action items\n- {line}", MEETING)[0]
    assert row["owner"] == owner


def test_lines_without_headings_are_sorted_by_keywords():
    notes = "Priya will send the recap tomorrow\nShould we move the launch?\nBlocked on legal review\nWe decided to ship v2"
    rows = {r["type"]: r for r in extract_rules(notes, MEETING)}
    assert rows["action"]["owner"] == "Priya" and rows["action"]["due"] == "2026-11-03"
    assert set(rows) == {"action", "question", "risk", "decision"}


def test_no_duplicates():
    rows = extract_rules("Risks\n- Budget\n- budget\n", MEETING)
    assert len(rows) == 1


# ---- Claude path (no real network calls) -------------------------------------------

AI_REPLY = {
    "decisions": ["Launch moves to Nov 24"],
    "action_items": [
        {"task": "send deck", "owner": "Priya", "due_text": "by Friday"},
        {"task": "fix bug", "owner": "Zed", "due_text": "next Tuesday"},   # Zed is not in the notes
        {"task": "write docs", "owner": "Unassigned", "due_text": ""},
    ],
    "follow_ups": [{"task": "ping finance", "owner": "", "due_text": "soon"}],
    "open_questions": ["Who owns slides?"],
    "risks": ["Migration may slip"],
}


def test_ai_output_is_checked_and_dates_come_from_code():
    rows = rows_from_ai_json(AI_REPLY, SAMPLE, MEETING)
    actions = by_type(rows, "action")
    assert [(r["text"], r["owner"], r["due"]) for r in actions] == [
        ("Send deck", "Priya", "2026-11-06"),
        ("Fix bug", UNASSIGNED, "2026-11-10"),   # invented owner removed
        ("Write docs", UNASSIGNED, ""),
    ]
    follow = by_type(rows, "follow_up")[0]
    assert follow["owner"] == UNASSIGNED and follow["due"] == "" and follow["due_text"] == "soon"


def test_uses_claude_when_key_is_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(extractor, "_call_claude", lambda notes, meeting: AI_REPLY)
    result = extract(SAMPLE, MEETING, use_ai=True)
    assert result["engine"] == "claude" and not result["warning"]


def test_falls_back_to_rules_when_claude_fails(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def boom(notes, meeting):
        raise RuntimeError("network down")

    monkeypatch.setattr(extractor, "_call_claude", boom)
    result = extract(SAMPLE, MEETING, use_ai=True)
    assert result["engine"] == "rules" and "RuntimeError" in result["warning"]
    assert len(result["rows"]) > 0


def test_works_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert extract(SAMPLE, MEETING, use_ai=False) ["warning"] == ""
    result = extract(SAMPLE, MEETING, use_ai=True)
    assert result["engine"] == "rules" and "ANTHROPIC_API_KEY" in result["warning"]
