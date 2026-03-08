#!/usr/bin/env python3
"""
run_pipeline.py — Single Command Demo Workflow

Runs the entire meeting action extraction pipeline on a transcript file
and launches the interactive task board.

Usage:
    python run_pipeline.py <transcript_file>
    python run_pipeline.py transcripts/demo_meeting.txt
    python run_pipeline.py                              # paste from stdin

Pipeline stages:
    STEP 1  Preprocessing        (spaCy sentence segmentation)
    STEP 2  Decision Detection   (Transformer NLI model)
    STEP 3  Decision Clustering  (Sentence embeddings)
    STEP 4  Decision Summarization (BART + cleaning)
    STEP 5  Task Generation      (QA + NER models)
    STEP 6  Task Board UI        (FastAPI server)
"""

import os
import sys
import shutil
import time
from pathlib import Path

# ── Apple Silicon safety: set BEFORE any ML imports ─────────────────────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ── Data paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent

RAW_TRANSCRIPT = PROJECT_ROOT / "data" / "raw_transcripts" / "meeting1.txt"
PROCESSED_TRANSCRIPT = PROJECT_ROOT / "data" / "processed_transcripts" / "meeting1.json"
DECISIONS_FILE = PROJECT_ROOT / "data" / "decision_sentences" / "meeting1_decisions.json"
CLUSTERS_FILE = PROJECT_ROOT / "data" / "decision_clusters" / "meeting1_clusters.json"
SUMMARIES_FILE = PROJECT_ROOT / "data" / "decision_summaries" / "meeting1_decisions.json"
TASKS_FILE = PROJECT_ROOT / "data" / "tasks" / "meeting1_tasks.json"


def banner(text: str) -> None:
    """Print a visible stage banner."""
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def load_transcript_from_file(path: Path) -> str:
    """Load transcript from a file path."""
    if not path.exists():
        print(f"✗ Transcript file not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def load_transcript_from_stdin() -> str:
    """Read transcript from stdin (interactive paste)."""
    print("Paste meeting transcript below, then press CTRL+D (Mac/Linux)")
    print("or CTRL+Z followed by Enter (Windows):")
    print("-" * 60)
    try:
        text = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)

    if not text.strip():
        print("✗ Empty transcript. Aborting.")
        sys.exit(1)
    return text


def step1_preprocess(raw_text: str) -> list:
    """STEP 1: Preprocess raw transcript into structured sentences."""
    from pipeline.preprocess import preprocess_transcript, save_processed_transcript

    sentences = preprocess_transcript(raw_text)
    save_processed_transcript(sentences, str(PROCESSED_TRANSCRIPT))
    return sentences


def step2_detect_decisions() -> list:
    """STEP 2: Detect decision-related sentences using NLI classifier."""
    from pipeline.decision_detector import detect_decisions_in_transcript

    decisions = detect_decisions_in_transcript(
        input_path=str(PROCESSED_TRANSCRIPT),
        output_path=str(DECISIONS_FILE),
        threshold=0.7,
    )
    return decisions


def step3_cluster() -> list:
    """STEP 3: Cluster related decision sentences."""
    from pipeline.clustering import cluster_decisions_in_transcript

    clusters = cluster_decisions_in_transcript(
        input_path=str(DECISIONS_FILE),
        output_path=str(CLUSTERS_FILE),
    )
    return clusters


def step4_summarize() -> list:
    """STEP 4: Generate concise decision summaries."""
    from pipeline.summarization import summarize_decisions_in_transcript

    summaries = summarize_decisions_in_transcript(
        input_path=str(CLUSTERS_FILE),
        output_path=str(SUMMARIES_FILE),
    )
    return summaries


def step5_generate_tasks() -> list:
    """STEP 5: Extract structured tasks from summaries."""
    from pipeline.task_generator import generate_tasks_from_transcript

    tasks = generate_tasks_from_transcript(
        summaries_path=str(SUMMARIES_FILE),
        transcript_path=str(PROCESSED_TRANSCRIPT),
        output_path=str(TASKS_FILE),
    )
    return tasks


def step6_launch_ui() -> None:
    """STEP 6: Launch the FastAPI task board."""
    import uvicorn

    print("\nStarting task board at  http://127.0.0.1:8000")
    print("Press CTRL+C to stop.\n")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


# ── Main ────────────────────────────────────────────────────────────────

def main():
    start = time.time()

    banner("MEETING ACTION EXTRACTION DEMO")

    # ── Resolve transcript source ───────────────────────────────────────
    if len(sys.argv) >= 2:
        transcript_path = Path(sys.argv[1])
        raw_text = load_transcript_from_file(transcript_path)
        print(f"\n✓ Transcript loaded: {transcript_path}")
    else:
        raw_text = load_transcript_from_stdin()
        print("\n✓ Transcript loaded from stdin")

    # Copy into the raw data folder so all paths stay consistent
    RAW_TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    RAW_TRANSCRIPT.write_text(raw_text, encoding="utf-8")

    line_count = len([l for l in raw_text.strip().splitlines() if l.strip()])
    print(f"  Lines: {line_count}")

    # ── STEP 1 ──────────────────────────────────────────────────────────
    banner("STEP 1 / 6 — Preprocessing")
    sentences = step1_preprocess(raw_text)
    print(f"✓ {len(sentences)} sentences extracted")
    print(f"  JSON → {PROCESSED_TRANSCRIPT.relative_to(PROJECT_ROOT)}")

    # ── STEP 2 ──────────────────────────────────────────────────────────
    banner("STEP 2 / 6 — Decision Detection")
    decisions = step2_detect_decisions()
    print(f"\n✓ {len(decisions)} decisions detected")
    print(f"  JSON → {DECISIONS_FILE.relative_to(PROJECT_ROOT)}")

    # ── STEP 3 ──────────────────────────────────────────────────────────
    banner("STEP 3 / 6 — Decision Clustering")
    clusters = step3_cluster()
    print(f"\n✓ {len(clusters)} clusters formed")
    print(f"  JSON → {CLUSTERS_FILE.relative_to(PROJECT_ROOT)}")

    # ── STEP 4 ──────────────────────────────────────────────────────────
    banner("STEP 4 / 6 — Decision Summarization")
    summaries = step4_summarize()
    print(f"\n✓ {len(summaries)} summaries generated")
    print(f"  JSON → {SUMMARIES_FILE.relative_to(PROJECT_ROOT)}")

    # ── STEP 5 ──────────────────────────────────────────────────────────
    banner("STEP 5 / 6 — Task Generation")
    tasks = step5_generate_tasks()
    print(f"\n✓ {len(tasks)} tasks generated")
    print(f"  JSON → {TASKS_FILE.relative_to(PROJECT_ROOT)}")

    # ── Results ─────────────────────────────────────────────────────────
    elapsed = time.time() - start
    banner("PIPELINE COMPLETE")
    print(f"\n  Sentences:  {len(sentences)}")
    print(f"  Decisions:  {len(decisions)}")
    print(f"  Clusters:   {len(clusters)}")
    print(f"  Summaries:  {len(summaries)}")
    print(f"  Tasks:      {len(tasks)}")
    print(f"  Time:       {elapsed:.1f}s")

    print("\n  JSON outputs:")
    print("  " + "-" * 56)
    json_outputs = [
        ("STEP 1", PROCESSED_TRANSCRIPT),
        ("STEP 2", DECISIONS_FILE),
        ("STEP 3", CLUSTERS_FILE),
        ("STEP 4", SUMMARIES_FILE),
        ("STEP 5", TASKS_FILE),
    ]
    for label, path in json_outputs:
        print(f"    {label}: {path.relative_to(PROJECT_ROOT)}")

    print("\n  Extracted tasks:")
    print("  " + "-" * 56)
    for task in tasks:
        deadline_str = f"  (deadline: {task['deadline']})" if task.get("deadline") else ""
        print(f"    • {task['title']}")
        print(f"      Assignee: {task['assignee']}{deadline_str}")
    print()

    # ── STEP 6 ──────────────────────────────────────────────────────────
    banner("STEP 6 / 6 — Task Board UI")
    step6_launch_ui()


if __name__ == "__main__":
    main()
