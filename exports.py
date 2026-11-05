"""Turn the (edited) table into a Jira CSV or a Slack message."""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Dict, List, Optional

UNASSIGNED = "Unassigned"
JIRA_COLUMNS = ["Summary", "Issue Type", "Assignee", "Due Date", "Description", "Labels"]
SECTIONS = [
    ("decision", "Decisions"),
    ("action", "Action items"),
    ("follow_up", "Follow-ups"),
    ("question", "Open questions"),
    ("risk", "Risks"),
]
LABELS = {"action": "action-item", "follow_up": "follow-up"}


def _iso(value: str) -> Optional[date]:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def _is_unassigned(owner: str) -> bool:
    return (owner or "").strip().lower() in ("", "unassigned")


def _csv_safe(value: str) -> str:
    # Stops spreadsheet apps from running a cell that starts with = + - or @ as a formula.
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def to_csv(rows: List[Dict[str, str]], meeting: date) -> str:
    """One Jira issue per action item / follow-up. Unassigned -> blank Assignee."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(JIRA_COLUMNS)
    for r in rows:
        if r["type"] not in LABELS or not r["text"].strip():
            continue
        text = r["text"].strip()
        description = f"From the meeting on {meeting.isoformat()}."
        if len(text) > 255:  # Jira's summary limit
            description += f"\n\nFull text: {text}"
        due = _iso(r.get("due", ""))
        writer.writerow([
            _csv_safe(text[:255]),
            "Task",
            "" if _is_unassigned(r.get("owner", "")) else _csv_safe(r["owner"].strip()),
            due.isoformat() if due else "",
            description,
            LABELS[r["type"]],
        ])
    return out.getvalue()


def _esc(text: str) -> str:
    # Slack needs these three characters escaped.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _short(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def to_slack(rows: List[Dict[str, str]], meeting: date) -> str:
    lines = [f"*Meeting notes — {_short(meeting)} {meeting.year}*"]
    for kind, title in SECTIONS:
        items = [r for r in rows if r["type"] == kind and r["text"].strip()]
        if not items:
            continue
        lines += ["", f"*{title}*"]
        for r in items:
            if kind in LABELS:
                owner = "_Unassigned_" if _is_unassigned(r.get("owner", "")) else f"*{_esc(r['owner'].strip())}*"
                due = _iso(r.get("due", ""))
                if due:
                    when = f" — due {_short(due)}"
                elif r.get("due_text"):
                    when = f" — due: {_esc(r['due_text'])}"
                else:
                    when = ""
                lines.append(f"• ☐ {_esc(r['text'].strip())} — {owner}{when}")
            else:
                lines.append(f"• {_esc(r['text'].strip())}")
    return "\n".join(lines)
