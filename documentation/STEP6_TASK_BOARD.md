# STEP 6: Task Board UI

## Overview

STEP 6 provides an interactive web interface for viewing extracted tasks and tracing them back to the original meeting transcript evidence. It is a read-only display layer that consumes outputs from previous pipeline steps without modifying them.

## Architecture

```
Browser
  │
  ├── GET /            → HTML task board page
  ├── GET /tasks       → JSON list of all tasks
  └── GET /evidence/N  → JSON transcript evidence for task N
  │
FastAPI Server (app/main.py)
  │
  ├── data/tasks/meeting1_tasks.json               ← STEP 5 output
  └── data/processed_transcripts/meeting1.json      ← STEP 1 output
```

**Stack:** FastAPI + Jinja2 templates + vanilla JavaScript

## Project Structure

```
app/
├── main.py              # FastAPI backend — endpoints & data loading
├── templates/
│   └── index.html       # Task board UI page
└── static/
    └── script.js        # Frontend logic — card rendering & evidence fetch
```

## API Endpoints

### `GET /`

Serves the task board HTML page.

### `GET /tasks`

Returns all tasks from STEP 5 output.

**Response:**
```json
[
  {
    "task_id": 0,
    "title": "Focus on the payment API",
    "assignee": "B",
    "deadline": null,
    "evidence_sentences": [4, 9],
    "cluster_id": 0
  }
]
```

### `GET /evidence/{task_id}`

Returns transcript evidence sentences for the specified task.

**Response:**
```json
{
  "task_id": 0,
  "evidence": [
    {
      "sentence_id": 4,
      "speaker": "B",
      "text": "I think we should focus on the payment API first"
    },
    {
      "sentence_id": 9,
      "speaker": "B",
      "text": "also we need to finalize the pricing model"
    }
  ]
}
```

**Errors:**
- `404` — Task ID not found

## Data Flow

```
Task board loads         →  GET /tasks
User clicks task         →  GET /evidence/{task_id}
Backend looks up task    →  finds evidence_sentences IDs
Backend looks up transcript → matches sentence_id to speaker + text
Frontend displays        →  evidence panel with speaker & quote
```

## UI Features

### Task Cards

Each task is displayed as a card showing:
- **Title** — decision summary from STEP 4
- **Assignee** — extracted by STEP 5 (shown as badge)
- **Deadline** — shown when available (shown as badge)
- **Show Evidence** button — toggles transcript evidence

### Evidence Panel

Clicking "Show Evidence" reveals:
- **Speaker** label
- **Quoted transcript text**
- **Sentence ID** reference

Evidence is fetched lazily on first click and cached in the DOM.

## Running the Server

```bash
# Install dependencies (if not already)
pip install fastapi uvicorn jinja2

# Start the server
uvicorn app.main:app --reload

# Open in browser
# http://127.0.0.1:8000
```

## Running Tests

```bash
python -m pytest test_task_board.py -v
```

Test coverage includes:
- Task list endpoint (structure, values, empty list)
- Evidence retrieval (single/multi sentence, speaker/text correctness)
- Error handling (invalid task_id, missing sentence in transcript)
- UI page serving (HTML, script inclusion)
- Data helpers (JSON loading, sentence index building)
- Integration with real pipeline data files

## Input Files

| File | Source | Contents |
|------|--------|----------|
| `data/tasks/meeting1_tasks.json` | STEP 5 | Structured tasks with assignee, deadline, evidence |
| `data/processed_transcripts/meeting1.json` | STEP 1 | Sentence-level transcript with speaker and text |

## Design Decisions

1. **Read-only** — STEP 6 never modifies pipeline outputs
2. **Lazy evidence loading** — evidence is fetched only when the user clicks, keeping initial page load fast
3. **No external CSS/JS frameworks** — vanilla HTML/CSS/JS for zero dependencies and fast loading
4. **Sentence index** — transcript sentences are indexed by ID at startup for O(1) evidence lookups
5. **Graceful handling** — missing sentence IDs in transcript are silently skipped, tasks without deadlines display correctly
