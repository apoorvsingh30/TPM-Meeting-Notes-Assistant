# Meeting Notes → Tasks

Paste messy meeting notes. Get back decisions, action items (with owner and due date), follow-ups, open questions and risks. Fix anything in a table, then download a Jira CSV or copy a Slack message.

- Runs locally. Python + FastAPI + one HTML page.
- Works with **no AI key**. Add a key and Claude reads the notes instead.

## Run it

You need Python 3.9 or newer.

**Mac / Linux**
```bash
cd meeting-notes-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Windows (PowerShell)**
```powershell
cd meeting-notes-tool
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:8000** and click **Load sample** → **Extract**.

## Use Claude (optional)

- Install the package: `pip install anthropic`
- Set your key, then start the app again:
  - Mac / Linux: `export ANTHROPIC_API_KEY=your-key`
  - Windows: `$env:ANTHROPIC_API_KEY="your-key"`
- A **Use Claude** tick box appears on the page.
- Change the model with `CLAUDE_MODEL` (default: `claude-sonnet-5-5`).
- If Claude fails for any reason, the app uses the built-in rules and shows a yellow note.
- Your notes are sent to Anthropic only when the tick box is on.

## How it behaves

**Owners**
- An owner is used only if the notes name one: `Priya will…`, `Priya to…`, `Marco: …`, `… (Marco)`, `… - Marco`, `Owner: Marco`, `assigned to Marco`, `@marco`.
- Anything else is **Unassigned**. "We", "I", "someone" and "the team" are never treated as owners.
- Names must start with a capital letter in the notes. `priya to send` stays Unassigned.
- With Claude, any owner that does not appear in your notes is reset to Unassigned.
- Unassigned cells are highlighted in yellow in the table.

**Dates** (all worked out from the meeting date you set, not from today)

| Notes say | Result |
|---|---|
| `by Friday` | the next Friday after the meeting day (a week later if the meeting is on a Friday) |
| `this Friday` | the Friday on or after the meeting day |
| `next Tuesday` | that weekday in the next calendar week (Mon–Sun) |
| `tomorrow`, `today`, `EOD` | meeting date +1, +0, +0 |
| `end of week` / `EOW` | Friday of the meeting week |
| `end of next week` | Friday of the following week |
| `end of month` / `EOM` | last day of the meeting month |
| `in 3 days`, `in 2 weeks`, `within 3 business days` | counted from the meeting date |
| `2026-11-12`, `Nov 12`, `12th November` | that date (no year → meeting year, or next year if it is long past) |

- Vague words like `next week` or `soon` are left blank. The original words show in the **From notes** column so you can set the date yourself.
- The page shows the original words next to every date, so you can check them quickly.

**What counts as what**
- Headings help most: `Decisions`, `Action items`, `Follow-ups`, `Open questions`, `Risks`.
- Inline labels work too: `Decision: …`, `Risk: …`, `Action: …`.
- Lines with no heading are sorted by keywords ("we decided", "blocked", "?", "need to"). Check these in the table.

## Export

**Jira CSV**
- Contains action items and follow-ups only. One Jira issue each.
- Columns: Summary, Issue Type (Task), Assignee, Due Date, Description, Labels.
- Unassigned items get an empty Assignee.
- In Jira: **⚙ Settings → System → External System Import → CSV**. Pick the file and map the columns. Set the date format to `yyyy-MM-dd`.
- Jira matches Assignee by user name, so check the mapping if your Jira uses emails or different names.

**Slack message**
- Click **Copy as Slack message**, then paste into Slack.
- The text also appears in a box on the page in case copying is blocked by your browser.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Files

- `app.py`: the web server and its four endpoints
- `index.html`: the whole page
- `extractor.py`: the rules, the Claude call and the owner checks
- `dates.py`: "by Friday" → real date
- `exports.py`: Jira CSV and Slack text
- `sample_notes.txt`: example notes
- `tests/`: automatic tests

## Limits

- The rule-based reader is simple. It works best when notes have headings and one item per line. Always check the table.
- English only.
- Nothing is saved. Refreshing the page clears the table.
