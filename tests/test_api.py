import csv
import io

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def sample():
    return client.get("/api/sample").json()


def test_home_page_loads():
    res = client.get("/")
    assert res.status_code == 200 and "Meeting Notes" in res.text


def test_status_without_key():
    assert client.get("/api/status").json() == {"ai_enabled": False}


def test_extract_sample():
    s = sample()
    assert s["meeting_date"] == "2026-11-02"
    res = client.post("/api/extract", json={"notes": s["notes"], "meeting_date": s["meeting_date"], "use_ai": False})
    data = res.json()
    assert data["engine"] == "rules"
    assert sum(r["type"] == "action" for r in data["rows"]) == 5


def test_extract_rejects_bad_date():
    res = client.post("/api/extract", json={"notes": "hi", "meeting_date": "not-a-date"})
    assert res.status_code == 422


ROWS = [
    {"type": "decision", "text": "Launch moves to Nov 24"},
    {"type": "action", "text": "Send deck", "owner": "Priya", "due": "2026-11-06"},
    {"type": "action", "text": "Update docs & FAQ <draft>", "owner": "Unassigned", "due": ""},
    {"type": "follow_up", "text": "=SUM(A1)", "owner": "Marco", "due": "2026-11-03"},
    {"type": "risk", "text": "Migration may slip"},
]


def test_csv_export_for_jira():
    res = client.post("/api/export/csv", json={"rows": ROWS, "meeting_date": "2026-11-02"})
    assert res.status_code == 200 and "attachment" in res.headers["content-disposition"]
    table = list(csv.DictReader(io.StringIO(res.text)))
    assert [r["Summary"] for r in table] == ["Send deck", "Update docs & FAQ <draft>", "'=SUM(A1)"]
    assert table[0]["Assignee"] == "Priya" and table[0]["Due Date"] == "2026-11-06"
    assert table[1]["Assignee"] == ""            # Unassigned -> blank, not the word "Unassigned"
    assert table[2]["Labels"] == "follow-up"


def test_slack_export():
    text = client.post("/api/export/slack", json={"rows": ROWS, "meeting_date": "2026-11-02"}).json()["text"]
    assert text.startswith("*Meeting notes — Mon 2 Nov 2026*")
    assert "• ☐ Send deck — *Priya* — due Fri 6 Nov" in text
    assert "• ☐ Update docs &amp; FAQ &lt;draft&gt; — _Unassigned_" in text
    assert "*Risks*" in text and "*Open questions*" not in text
