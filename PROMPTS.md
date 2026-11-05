# How this was built

This tool was built in one conversation between me (a project manager) and Claude, an AI assistant made by Anthropic. This page explains what I asked for, what Claude did, and what has and has not been checked.

## 1. What I asked for

- A small web app where I paste messy meeting notes.
- It gives back decisions, action items (owner and due date), follow-ups, open questions and risks.
- Words like "by Friday" or "next Tuesday" must become real dates, counted from the meeting date.
- If the notes do not say who owns something, it must say "Unassigned" and never guess.
- I can fix mistakes in a table, then download a CSV for Jira or copy a Slack message.
- Python with FastAPI and one simple HTML page. Small and easy to run.
- It must work with no AI key, and use Claude only if I add a key.
- Also: a few tests, sample notes, and a README.
- I asked Claude to tell me its plan in a few simple lines before writing code.

## 2. The plan Claude gave first

- Built-in rules read the notes, so no key is needed. Claude is optional.
- Code (not the AI) works out the dates, so they are always correct and repeatable.
- Owners are never guessed. If Claude (the AI) names an owner who is not in the notes, the tool resets it to "Unassigned".
- One small FastAPI app and one HTML page with an editable table.
- Tests, sample notes and a README.

## 3. What Claude built

- `dates.py`: turns date words into real dates.
- `extractor.py`: finds the items and owners, and can call Claude.
- `exports.py`: makes the Jira CSV and the Slack message.
- `app.py` and `index.html`: the server and the page.
- `sample_notes.txt`, `tests/`, `README.md`: example notes, automatic checks and run steps.

## 4. How it was checked

- Claude wrote 60 automatic tests and ran them. All pass.
- One test failed at first because my expected text was wrong (the tool removes a final full stop on purpose). Claude fixed the test, not the tool.
- Claude started the app and called every endpoint on the sample notes. The table data, the Jira CSV and the Slack message all came out as expected.
- Claude checked that the page's script has no syntax errors.

## 5. What has NOT been checked

- The page was not clicked through in a real browser.
- The Claude (AI) path was tested only with a pretend reply, not a live call with a real key.
- The no-key rules are simple. They work best when notes have headings like "Action items". Lines with no heading are sorted by keywords and may be wrong, which is why the table is editable.

## 6. Choices worth knowing about

- "By Friday" said on a Friday means next week's Friday.
- "Next Tuesday" means that day in the following Monday to Sunday week.
- Vague words like "next week" or "soon" are left blank, with the original words shown beside the date so I can set it myself.
- Only action items and follow-ups go into the Jira CSV.

## 7. Credit

- The idea, the requirements and the decisions are mine.
- The code, tests and docs were written by Claude from my instructions, and I am responsible for how I use them.
