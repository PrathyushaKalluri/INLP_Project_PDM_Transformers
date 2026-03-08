"""
STEP 6: Task Board UI — FastAPI Backend

Serves the interactive task board and provides API endpoints
for retrieving tasks and their transcript evidence.

Endpoints:
    GET /            — Serve the task board UI
    GET /tasks       — Return all tasks from STEP 5 output
    GET /evidence/{task_id} — Return transcript evidence for a task

Data sources:
    data/tasks/meeting1_tasks.json              — STEP 5 output
    data/processed_transcripts/meeting1.json    — STEP 1 output
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve paths relative to project root (one level up from app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

TASKS_PATH = PROJECT_ROOT / "data" / "tasks" / "meeting1_tasks.json"
TRANSCRIPT_PATH = PROJECT_ROOT / "data" / "processed_transcripts" / "meeting1.json"

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> list:
    """Load a JSON file and return its contents."""
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tasks() -> list[dict]:
    """Load tasks produced by STEP 5."""
    return load_json(TASKS_PATH)


def load_transcript() -> list[dict]:
    """Load processed transcript from STEP 1."""
    return load_json(TRANSCRIPT_PATH)


def build_sentence_index(transcript: list[dict]) -> dict[int, dict]:
    """Build a lookup from sentence_id → sentence dict for O(1) access."""
    return {s["sentence_id"]: s for s in transcript}


# ---------------------------------------------------------------------------
# Pre-load data at startup
# ---------------------------------------------------------------------------

_tasks: list[dict] = []
_sentence_index: dict[int, dict] = {}


def _init_data() -> None:
    """Load data files into module-level caches."""
    global _tasks, _sentence_index
    _tasks = load_tasks()
    transcript = load_transcript()
    _sentence_index = build_sentence_index(transcript)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Load pipeline data when the server starts."""
    _init_data()
    yield


app = FastAPI(
    title="Meeting Task Board",
    description="STEP 6 — Interactive task board with evidence traceability",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files and templates
APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the task board UI."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/tasks")
async def get_tasks():
    """Return all tasks from STEP 5 output.

    Returns:
        list[dict]: Each task contains task_id, title, assignee,
                    deadline, evidence_sentences, and cluster_id.
    """
    return _tasks


@app.get("/evidence/{task_id}")
async def get_evidence(task_id: int):
    """Return transcript evidence sentences for a given task.

    Args:
        task_id: The numeric task ID from the tasks file.

    Returns:
        dict: Contains task_id and a list of evidence entries,
              each with sentence_id, speaker, and text.

    Raises:
        404: If the task_id is not found.
    """
    # Find the task
    task = None
    for t in _tasks:
        if t["task_id"] == task_id:
            task = t
            break

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Look up evidence sentences in the transcript
    evidence = []
    for sid in task.get("evidence_sentences", []):
        sentence = _sentence_index.get(sid)
        if sentence:
            evidence.append({
                "sentence_id": sentence["sentence_id"],
                "speaker": sentence["speaker"],
                "text": sentence["text"],
            })

    return {
        "task_id": task_id,
        "evidence": evidence,
    }
