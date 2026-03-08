"""
Tests for the task generation module (STEP 5).

Tests cover:
- Task structure validation (all required fields)
- Assignee extraction (QA model + fallback)
- Deadline extraction (NER + regex fallback)
- 1:1 mapping (summaries → tasks)
- Evidence sentence preservation
- Title derivation from summary
- Edge cases (empty inputs, missing evidence, multiple sentences)
- I/O helpers (load, save)
- End-to-end integration with real pipeline data
"""

import json
import os
import tempfile
from pathlib import Path

# ── Apple Silicon safety ────────────────────────────────────────────────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pipeline.task_generator import (
    TaskGenerator,
    load_summaries,
    load_transcript,
    save_tasks,
    generate_tasks_from_transcript,
    DEADLINE_PATTERNS,
)


# ── Test data ───────────────────────────────────────────────────────────

SAMPLE_TRANSCRIPT = [
    {"sentence_id": 1, "speaker": "A", "text": "good morning everyone."},
    {"sentence_id": 2, "speaker": "A", "text": "let's start with the Q1 planning"},
    {"sentence_id": 3, "speaker": "B", "text": "thanks for having us."},
    {"sentence_id": 4, "speaker": "B",
     "text": "I think we should focus on the payment API first"},
    {"sentence_id": 5, "speaker": "A", "text": "absolutely."},
    {"sentence_id": 6, "speaker": "A",
     "text": "we need to deploy it by end of march."},
    {"sentence_id": 7, "speaker": "A",
     "text": "can you prepare the technical spec?"},
    {"sentence_id": 8, "speaker": "B",
     "text": "yes I'll have it ready by friday."},
    {"sentence_id": 9, "speaker": "B",
     "text": "also we need to finalize the pricing model"},
    {"sentence_id": 10, "speaker": "C", "text": "I can help with the pricing."},
    {"sentence_id": 15, "speaker": "C",
     "text": "I will also prepare the documentation"},
    {"sentence_id": 18, "speaker": "A",
     "text": "let's aim for next wednesday"},
]

SAMPLE_SUMMARIES = [
    {
        "cluster_id": 0,
        "summary": "Focus on the payment API.",
        "evidence_sentences": [4, 9],
    },
    {
        "cluster_id": 1,
        "summary": "Aim for next Wednesday.",
        "evidence_sentences": [18],
    },
    {
        "cluster_id": 2,
        "summary": "Deploy the system by end of March.",
        "evidence_sentences": [6],
    },
    {
        "cluster_id": 3,
        "summary": "Prepare the documentation.",
        "evidence_sentences": [15],
    },
    {
        "cluster_id": 4,
        "summary": "Prepare the technical spec.",
        "evidence_sentences": [7],
    },
]


def main():
    print("=" * 70)
    print("STEP 5: TASK GENERATION — TEST SUITE")
    print("=" * 70)

    passed = 0
    failed = 0

    def check(test_name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {test_name}")
            passed += 1
        else:
            print(f"  ✗ {test_name}")
            if detail:
                print(f"      {detail}")
            failed += 1

    # ── Initialize generator ────────────────────────────────────────────
    print("\n[1] INITIALIZING TASK GENERATOR")
    print("-" * 70)

    generator = TaskGenerator()
    qa_available = generator._qa_model is not None
    ner_available = generator._nlp is not None
    print(f"  QA model available:  {qa_available}")
    print(f"  NER model available: {ner_available}")
    print(f"  (Tests work with or without models)\n")

    # ── Test: Required task fields ──────────────────────────────────────
    print("\n[2] TASK STRUCTURE VALIDATION")
    print("-" * 70)

    task = generator.generate_task(SAMPLE_SUMMARIES[0], SAMPLE_TRANSCRIPT)
    required_fields = ["task_id", "title", "assignee", "deadline",
                        "evidence_sentences", "cluster_id"]
    for field in required_fields:
        check(f"Has field '{field}'", field in task)

    check("task_id is int", isinstance(task["task_id"], int))
    check("title is str", isinstance(task["title"], str))
    check("assignee is str", isinstance(task["assignee"], str))
    check(
        "deadline is str or None",
        task["deadline"] is None or isinstance(task["deadline"], str),
    )
    check("evidence_sentences is list", isinstance(task["evidence_sentences"], list))
    check("cluster_id is int", isinstance(task["cluster_id"], int))

    # ── Test: Title derivation ──────────────────────────────────────────
    print("\n[3] TITLE DERIVATION FROM SUMMARY")
    print("-" * 70)

    title_tests = [
        (SAMPLE_SUMMARIES[0], "Focus on the payment API"),
        (SAMPLE_SUMMARIES[2], "Deploy the system by end of March"),
        (SAMPLE_SUMMARIES[3], "Prepare the documentation"),
        (SAMPLE_SUMMARIES[4], "Prepare the technical spec"),
    ]

    for summary, expected_title in title_tests:
        task = generator.generate_task(summary, SAMPLE_TRANSCRIPT)
        check(
            f"Cluster {summary['cluster_id']}: title = \"{task['title']}\"",
            task["title"] == expected_title,
            f"Expected \"{expected_title}\", got \"{task['title']}\"",
        )
        check(
            f"Cluster {summary['cluster_id']}: no trailing period in title",
            not task["title"].endswith("."),
        )

    # ── Test: Evidence preservation ─────────────────────────────────────
    print("\n[4] EVIDENCE SENTENCE PRESERVATION")
    print("-" * 70)

    for summary in SAMPLE_SUMMARIES:
        task = generator.generate_task(summary, SAMPLE_TRANSCRIPT)
        check(
            f"Cluster {summary['cluster_id']}: evidence IDs preserved",
            task["evidence_sentences"] == summary["evidence_sentences"],
            f"Expected {summary['evidence_sentences']}, got {task['evidence_sentences']}",
        )
        check(
            f"Cluster {summary['cluster_id']}: cluster_id preserved",
            task["cluster_id"] == summary["cluster_id"],
        )

    # ── Test: Assignee extraction (fallback) ────────────────────────────
    print("\n[5] ASSIGNEE EXTRACTION (FALLBACK)")
    print("-" * 70)

    # "I will also prepare the documentation" — speaker C self-assigns
    task_c = generator.generate_task(SAMPLE_SUMMARIES[3], SAMPLE_TRANSCRIPT)
    check(
        "Self-assignment: 'I will' → speaker C",
        task_c["assignee"] == "C",
        f"Got: \"{task_c['assignee']}\"",
    )

    # "I think we should focus..." — speaker B
    task_b = generator.generate_task(SAMPLE_SUMMARIES[0], SAMPLE_TRANSCRIPT)
    check(
        "Speaker-based fallback: cluster 0 → speaker B",
        task_b["assignee"] == "B",
        f"Got: \"{task_b['assignee']}\"",
    )

    # "can you prepare the technical spec?" — speaker A delegates
    task_a = generator.generate_task(SAMPLE_SUMMARIES[4], SAMPLE_TRANSCRIPT)
    check(
        "Delegation: 'can you' → speaker A",
        task_a["assignee"] == "A",
        f"Got: \"{task_a['assignee']}\"",
    )

    # Check that no assignee is empty
    for summary in SAMPLE_SUMMARIES:
        task = generator.generate_task(summary, SAMPLE_TRANSCRIPT)
        check(
            f"Cluster {summary['cluster_id']}: assignee not empty",
            task["assignee"] and task["assignee"].strip() != "",
        )

    # ── Test: Deadline extraction (regex fallback) ──────────────────────
    print("\n[6] DEADLINE EXTRACTION (REGEX FALLBACK)")
    print("-" * 70)

    # Test deadline extraction (NER when available, regex fallback)
    # The NER model may extract a narrower span than regex (e.g. "March"
    # instead of "end of March"), so we test that the core date word is present.
    regex_tests = [
        ("Deploy the system by end of March.", "March"),
        ("Aim for next Wednesday.", "Wednesday"),
        ("Finish by tomorrow.", "tomorrow"),
        ("No deadline here.", None),
        ("Focus on the payment API.", None),
    ]

    for text, expected in regex_tests:
        deadline = generator.extract_deadline(text, [])
        if expected is None:
            check(
                f"\"{text[:40]}\" → None",
                deadline is None,
                f"Expected None, got \"{deadline}\"",
            )
        else:
            check(
                f"\"{text[:40]}\" → \"{deadline}\"",
                deadline is not None and expected.lower() in deadline.lower(),
                f"Expected \"{expected}\", got \"{deadline}\"",
            )

    # Test deadline from evidence sentences
    deadline_from_evidence = generator.extract_deadline(
        "Prepare the documentation.",
        ["we need to deploy it by end of march."],
    )
    check(
        "Deadline from evidence: 'end of march'",
        deadline_from_evidence is not None,
        f"Got: {deadline_from_evidence}",
    )

    # ── Test: Full task with deadline ───────────────────────────────────
    print("\n[7] TASKS WITH DEADLINES")
    print("-" * 70)

    # Cluster 2: "Deploy the system by end of March." — has deadline in summary
    task_deadline = generator.generate_task(SAMPLE_SUMMARIES[2], SAMPLE_TRANSCRIPT)
    check(
        "Cluster 2: deadline detected",
        task_deadline["deadline"] is not None,
        f"Got: {task_deadline['deadline']}",
    )

    # Cluster 1: "Aim for next Wednesday." — has deadline
    task_wed = generator.generate_task(SAMPLE_SUMMARIES[1], SAMPLE_TRANSCRIPT)
    check(
        "Cluster 1: deadline detected",
        task_wed["deadline"] is not None,
        f"Got: {task_wed['deadline']}",
    )

    # Cluster 3: "Prepare the documentation." — no deadline
    task_nodl = generator.generate_task(SAMPLE_SUMMARIES[3], SAMPLE_TRANSCRIPT)
    check(
        "Cluster 3: no deadline (correct)",
        task_nodl["deadline"] is None,
        f"Got: {task_nodl['deadline']}",
    )

    # ── Test: 1:1 mapping ───────────────────────────────────────────────
    print("\n[8] 1:1 MAPPING (SUMMARIES → TASKS)")
    print("-" * 70)

    tasks = generator.generate_tasks(SAMPLE_SUMMARIES, SAMPLE_TRANSCRIPT)
    check(
        f"Number of tasks ({len(tasks)}) == summaries ({len(SAMPLE_SUMMARIES)})",
        len(tasks) == len(SAMPLE_SUMMARIES),
    )

    for i, (summary, task) in enumerate(zip(SAMPLE_SUMMARIES, tasks)):
        check(
            f"Task {i}: cluster_id matches",
            task["cluster_id"] == summary["cluster_id"],
        )
        check(
            f"Task {i}: task_id == cluster_id",
            task["task_id"] == summary["cluster_id"],
        )

    # ── Test: I/O helpers ───────────────────────────────────────────────
    print("\n[9] I/O HELPERS")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save summaries
        summaries_path = os.path.join(tmpdir, "summaries.json")
        with open(summaries_path, "w") as f:
            json.dump(SAMPLE_SUMMARIES, f)

        # Save transcript
        transcript_path = os.path.join(tmpdir, "transcript.json")
        with open(transcript_path, "w") as f:
            json.dump(SAMPLE_TRANSCRIPT, f)

        # Load summaries
        loaded_summaries = load_summaries(summaries_path)
        check("load_summaries reads correct count", len(loaded_summaries) == 5)

        # Load transcript
        loaded_transcript = load_transcript(transcript_path)
        check("load_transcript reads correct count", len(loaded_transcript) == 12)

        # Save tasks
        tasks_path = os.path.join(tmpdir, "sub", "tasks.json")
        save_tasks(tasks, tasks_path)
        check("save_tasks creates file", os.path.exists(tasks_path))
        check(
            "save_tasks creates parent dirs",
            os.path.exists(os.path.join(tmpdir, "sub")),
        )

        with open(tasks_path, "r") as f:
            reloaded = json.load(f)
        check("save_tasks correct count", len(reloaded) == len(tasks))

    # ── Test: End-to-end with real data ─────────────────────────────────
    print("\n[10] END-TO-END WITH REAL DATA")
    print("-" * 70)

    real_summaries_path = "data/decision_summaries/meeting1_decisions.json"
    real_transcript_path = "data/processed_transcripts/meeting1.json"

    if os.path.exists(real_summaries_path) and os.path.exists(real_transcript_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "meeting1_tasks.json")
            tasks = generate_tasks_from_transcript(
                summaries_path=real_summaries_path,
                transcript_path=real_transcript_path,
                output_path=output_path,
            )

            real_summaries = load_summaries(real_summaries_path)
            check(
                f"Real data: {len(tasks)} tasks for {len(real_summaries)} summaries",
                len(tasks) == len(real_summaries),
            )
            check("Real data: output file created", os.path.exists(output_path))

            # Verify all tasks are well-formed
            for t in tasks:
                check(
                    f"Real Task {t['task_id']}: has title",
                    bool(t["title"]),
                    f"Got: \"{t['title']}\"",
                )
                check(
                    f"Real Task {t['task_id']}: has assignee",
                    bool(t["assignee"]),
                    f"Got: \"{t['assignee']}\"",
                )
                check(
                    f"Real Task {t['task_id']}: no trailing period in title",
                    not t["title"].endswith("."),
                    f"Got: \"{t['title']}\"",
                )
                check(
                    f"Real Task {t['task_id']}: has evidence",
                    len(t["evidence_sentences"]) > 0,
                )
    else:
        print(f"  ⚠ Skipping: real data files not found")
        print("    Run STEP 1–4 first")

    # ── Test: Edge cases ────────────────────────────────────────────────
    print("\n[11] EDGE CASES")
    print("-" * 70)

    # No summaries
    empty_tasks = generator.generate_tasks([], SAMPLE_TRANSCRIPT)
    check("Empty summaries → empty tasks", empty_tasks == [])

    # Missing evidence sentence IDs (not in transcript)
    orphan_summary = {
        "cluster_id": 99,
        "summary": "Do something.",
        "evidence_sentences": [999],  # doesn't exist in transcript
    }
    orphan_task = generator.generate_task(orphan_summary, SAMPLE_TRANSCRIPT)
    check(
        "Missing evidence: still produces task",
        orphan_task["task_id"] == 99,
    )
    check(
        "Missing evidence: assignee defaults to Unknown",
        orphan_task["assignee"] == "Unknown",
        f"Got: \"{orphan_task['assignee']}\"",
    )

    # Summary without deadline — use evidence that has no time words
    # (NER may flag words like "morning" as a time entity)
    no_deadline_summary = {
        "cluster_id": 88,
        "summary": "Review the code.",
        "evidence_sentences": [],
    }
    no_deadline_task = generator.generate_task(no_deadline_summary, SAMPLE_TRANSCRIPT)
    check(
        "No deadline in text → deadline is None",
        no_deadline_task["deadline"] is None,
        f"Got: \"{no_deadline_task['deadline']}\"",
    )

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) need attention")

    return failed == 0


if __name__ == "__main__":
    main()
