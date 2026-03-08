"""
Tests for STEP 6: Task Board UI — FastAPI Backend

Covers:
    - Task list endpoint
    - Evidence retrieval endpoint
    - Error handling (invalid task_id)
    - Data loading helpers
    - Sentence index building
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_TASKS = [
    {
        "task_id": 0,
        "title": "Focus on the payment API",
        "assignee": "B",
        "deadline": None,
        "evidence_sentences": [4, 9],
        "cluster_id": 0,
    },
    {
        "task_id": 1,
        "title": "Aim for next Wednesday",
        "assignee": "A",
        "deadline": "next Wednesday",
        "evidence_sentences": [18],
        "cluster_id": 1,
    },
    {
        "task_id": 2,
        "title": "Deploy the system by end of March",
        "assignee": "A",
        "deadline": "end of March",
        "evidence_sentences": [6],
        "cluster_id": 2,
    },
    {
        "task_id": 3,
        "title": "Prepare the documentation",
        "assignee": "C",
        "deadline": None,
        "evidence_sentences": [15],
        "cluster_id": 3,
    },
    {
        "task_id": 4,
        "title": "Prepare the technical spec",
        "assignee": "A",
        "deadline": None,
        "evidence_sentences": [7],
        "cluster_id": 4,
    },
]

SAMPLE_TRANSCRIPT = [
    {"sentence_id": 4, "speaker": "B", "text": "I think we should focus on the payment API first"},
    {"sentence_id": 6, "speaker": "A", "text": "we need to deploy it by end of march."},
    {"sentence_id": 7, "speaker": "A", "text": "can you prepare the technical spec?"},
    {"sentence_id": 9, "speaker": "B", "text": "also we need to finalize the pricing model"},
    {"sentence_id": 15, "speaker": "C", "text": "I will also prepare the documentation"},
    {"sentence_id": 18, "speaker": "A", "text": "let's aim for next wednesday"},
]


# ---------------------------------------------------------------------------
# Helpers to set up a test client with patched data
# ---------------------------------------------------------------------------


def _make_client(tasks=None, transcript=None):
    """Create a TestClient with the given data injected."""
    import app.main as main_module

    if tasks is None:
        tasks = SAMPLE_TASKS
    if transcript is None:
        transcript = SAMPLE_TRANSCRIPT

    main_module._tasks = tasks
    main_module._sentence_index = main_module.build_sentence_index(transcript)
    return TestClient(main_module.app)


# ===================================================================
# Test classes
# ===================================================================


class TestGetTasks(unittest.TestCase):
    """Tests for GET /tasks."""

    def setUp(self):
        self.client = _make_client()

    def test_returns_200(self):
        r = self.client.get("/tasks")
        self.assertEqual(r.status_code, 200)

    def test_returns_all_tasks(self):
        r = self.client.get("/tasks")
        data = r.json()
        self.assertEqual(len(data), 5)

    def test_task_structure(self):
        r = self.client.get("/tasks")
        task = r.json()[0]
        for key in ("task_id", "title", "assignee", "deadline", "evidence_sentences", "cluster_id"):
            self.assertIn(key, task, f"Missing key: {key}")

    def test_task_values(self):
        r = self.client.get("/tasks")
        task = r.json()[0]
        self.assertEqual(task["task_id"], 0)
        self.assertEqual(task["title"], "Focus on the payment API")
        self.assertEqual(task["assignee"], "B")
        self.assertIsNone(task["deadline"])
        self.assertEqual(task["evidence_sentences"], [4, 9])

    def test_task_with_deadline(self):
        r = self.client.get("/tasks")
        task = r.json()[2]
        self.assertEqual(task["deadline"], "end of March")

    def test_empty_tasks(self):
        client = _make_client(tasks=[])
        r = client.get("/tasks")
        self.assertEqual(r.json(), [])


class TestGetEvidence(unittest.TestCase):
    """Tests for GET /evidence/{task_id}."""

    def setUp(self):
        self.client = _make_client()

    def test_returns_200(self):
        r = self.client.get("/evidence/0")
        self.assertEqual(r.status_code, 200)

    def test_evidence_structure(self):
        r = self.client.get("/evidence/0")
        data = r.json()
        self.assertIn("task_id", data)
        self.assertIn("evidence", data)
        self.assertEqual(data["task_id"], 0)

    def test_evidence_entries(self):
        r = self.client.get("/evidence/0")
        ev = r.json()["evidence"]
        self.assertEqual(len(ev), 2)
        # Check each entry has required fields
        for entry in ev:
            self.assertIn("sentence_id", entry)
            self.assertIn("speaker", entry)
            self.assertIn("text", entry)

    def test_evidence_content(self):
        r = self.client.get("/evidence/0")
        ev = r.json()["evidence"]
        speakers = [e["speaker"] for e in ev]
        self.assertEqual(speakers, ["B", "B"])
        sids = [e["sentence_id"] for e in ev]
        self.assertEqual(sids, [4, 9])

    def test_single_evidence_sentence(self):
        r = self.client.get("/evidence/3")
        ev = r.json()["evidence"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["speaker"], "C")
        self.assertIn("documentation", ev[0]["text"])

    def test_evidence_with_deadline_task(self):
        r = self.client.get("/evidence/1")
        ev = r.json()["evidence"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["sentence_id"], 18)
        self.assertIn("wednesday", ev[0]["text"].lower())

    def test_task_not_found(self):
        r = self.client.get("/evidence/999")
        self.assertEqual(r.status_code, 404)

    def test_negative_task_id(self):
        r = self.client.get("/evidence/-1")
        self.assertEqual(r.status_code, 404)

    def test_all_tasks_have_evidence(self):
        """Every task must return at least one evidence sentence."""
        for task in SAMPLE_TASKS:
            r = self.client.get(f"/evidence/{task['task_id']}")
            self.assertEqual(r.status_code, 200)
            ev = r.json()["evidence"]
            self.assertGreater(len(ev), 0, f"Task {task['task_id']} has no evidence")


class TestEvidenceTraceability(unittest.TestCase):
    """Ensure evidence maps correctly back to the transcript."""

    def setUp(self):
        self.client = _make_client()

    def test_speaker_matches_transcript(self):
        """Evidence speaker should match the processed transcript."""
        r = self.client.get("/evidence/3")
        ev = r.json()["evidence"]
        self.assertEqual(ev[0]["speaker"], "C")

    def test_text_matches_transcript(self):
        r = self.client.get("/evidence/3")
        ev = r.json()["evidence"]
        self.assertEqual(ev[0]["text"], "I will also prepare the documentation")

    def test_sentence_id_matches(self):
        r = self.client.get("/evidence/3")
        ev = r.json()["evidence"]
        self.assertEqual(ev[0]["sentence_id"], 15)


class TestUIPage(unittest.TestCase):
    """Tests for the task board HTML page."""

    def setUp(self):
        self.client = _make_client()

    def test_index_returns_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_index_returns_html(self):
        r = self.client.get("/")
        self.assertIn("text/html", r.headers["content-type"])

    def test_index_contains_title(self):
        r = self.client.get("/")
        self.assertIn("Meeting", r.text)

    def test_index_loads_script(self):
        r = self.client.get("/")
        self.assertIn("script.js", r.text)


class TestBuildSentenceIndex(unittest.TestCase):
    """Tests for the build_sentence_index helper."""

    def test_basic_index(self):
        from app.main import build_sentence_index

        transcript = [
            {"sentence_id": 1, "speaker": "A", "text": "hello"},
            {"sentence_id": 5, "speaker": "B", "text": "world"},
        ]
        idx = build_sentence_index(transcript)
        self.assertEqual(len(idx), 2)
        self.assertIn(1, idx)
        self.assertIn(5, idx)
        self.assertEqual(idx[1]["speaker"], "A")

    def test_empty_transcript(self):
        from app.main import build_sentence_index

        idx = build_sentence_index([])
        self.assertEqual(idx, {})


class TestLoadJson(unittest.TestCase):
    """Tests for the load_json helper."""

    def test_loads_valid_file(self):
        from app.main import load_json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"a": 1}], f)
            f.flush()
            path = Path(f.name)

        try:
            result = load_json(path)
            self.assertEqual(result, [{"a": 1}])
        finally:
            path.unlink()

    def test_missing_file_raises(self):
        from app.main import load_json

        with self.assertRaises(FileNotFoundError):
            load_json(Path("/nonexistent/file.json"))


class TestStaticAssets(unittest.TestCase):
    """Tests that static files are served."""

    def setUp(self):
        self.client = _make_client()

    def test_script_js_accessible(self):
        r = self.client.get("/static/script.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("loadTasks", r.text)


class TestEdgeCases(unittest.TestCase):
    """Edge-case tests."""

    def test_missing_evidence_sentence_in_transcript(self):
        """If a sentence_id in evidence_sentences is not in the transcript,
        it should be silently skipped (not crash)."""
        tasks = [
            {
                "task_id": 0,
                "title": "Test",
                "assignee": "X",
                "deadline": None,
                "evidence_sentences": [999],  # not in transcript
                "cluster_id": 0,
            }
        ]
        client = _make_client(tasks=tasks)
        r = client.get("/evidence/0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["evidence"], [])

    def test_task_without_evidence_sentences_key(self):
        """Tasks missing evidence_sentences should return empty evidence."""
        tasks = [
            {
                "task_id": 0,
                "title": "Test",
                "assignee": "X",
                "deadline": None,
                "cluster_id": 0,
                # evidence_sentences is missing
            }
        ]
        client = _make_client(tasks=tasks)
        r = client.get("/evidence/0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["evidence"], [])


class TestWithRealData(unittest.TestCase):
    """Integration tests using the actual pipeline output files."""

    @classmethod
    def setUpClass(cls):
        """Skip if data files don't exist."""
        project = Path(__file__).resolve().parent
        cls.tasks_path = project / "data" / "tasks" / "meeting1_tasks.json"
        cls.transcript_path = project / "data" / "processed_transcripts" / "meeting1.json"
        if not cls.tasks_path.exists() or not cls.transcript_path.exists():
            raise unittest.SkipTest("Pipeline data files not found")

    def setUp(self):
        from app.main import load_json, build_sentence_index

        self.tasks = load_json(self.tasks_path)
        transcript = load_json(self.transcript_path)
        self.index = build_sentence_index(transcript)

        import app.main as m
        m._tasks = self.tasks
        m._sentence_index = self.index
        self.client = TestClient(m.app)

    def test_all_tasks_loaded(self):
        r = self.client.get("/tasks")
        self.assertEqual(len(r.json()), len(self.tasks))

    def test_every_task_has_valid_evidence(self):
        for task in self.tasks:
            r = self.client.get(f"/evidence/{task['task_id']}")
            self.assertEqual(r.status_code, 200)
            ev = r.json()["evidence"]
            self.assertEqual(len(ev), len(task["evidence_sentences"]))

    def test_evidence_speakers_not_empty(self):
        for task in self.tasks:
            r = self.client.get(f"/evidence/{task['task_id']}")
            for entry in r.json()["evidence"]:
                self.assertTrue(len(entry["speaker"]) > 0)
                self.assertTrue(len(entry["text"]) > 0)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
