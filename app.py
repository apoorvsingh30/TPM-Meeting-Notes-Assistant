"""Meeting Notes -> Tasks. Run with:  python app.py   (then open http://127.0.0.1:8000)"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

import exports
from extractor import ai_available, extract

BASE = Path(__file__).parent
app = FastAPI(title="Meeting Notes to Tasks")


class ExtractIn(BaseModel):
    notes: str = Field(..., max_length=100_000)
    meeting_date: Optional[date] = None  # defaults to today
    use_ai: bool = True


class RowIn(BaseModel):
    type: Literal["decision", "action", "follow_up", "question", "risk"]
    text: str = ""
    owner: str = ""
    due: str = ""
    due_text: str = ""


class ExportIn(BaseModel):
    rows: List[RowIn]
    meeting_date: Optional[date] = None


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE / "index.html")


@app.get("/api/status")
def status() -> dict:
    return {"ai_enabled": ai_available()}


@app.get("/api/sample")
def sample() -> dict:
    notes = (BASE / "sample_notes.txt").read_text(encoding="utf-8")
    m = re.search(r"meeting date:\s*(\d{4}-\d{2}-\d{2})", notes, re.I)
    return {"notes": notes, "meeting_date": m.group(1) if m else date.today().isoformat()}


@app.post("/api/extract")
def api_extract(body: ExtractIn) -> dict:
    return extract(body.notes, body.meeting_date or date.today(), body.use_ai)


@app.post("/api/export/csv")
def export_csv(body: ExportIn) -> Response:
    meeting = body.meeting_date or date.today()
    content = exports.to_csv([r.model_dump() for r in body.rows], meeting)
    return Response(content, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="jira-tasks-{meeting.isoformat()}.csv"'})


@app.post("/api/export/slack")
def export_slack(body: ExportIn) -> dict:
    meeting = body.meeting_date or date.today()
    return {"text": exports.to_slack([r.model_dump() for r in body.rows], meeting)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
