"""
Example usage of the task generation module (STEP 5).

Demonstrates:
1. Loading decision summaries from STEP 4
2. Loading transcript sentences from STEP 1
3. Initializing ML-based task generator (QA + NER)
4. Generating structured tasks with assignee and deadline extraction
5. Saving tasks for downstream display (STEP 6)
6. Analyzing task quality
"""

from pipeline.task_generator import (
    TaskGenerator,
    load_summaries,
    load_transcript,
    save_tasks,
    generate_tasks_from_transcript,
)


def main():
    """Run task generation on decision summaries."""

    print("=" * 70)
    print("NLP PIPELINE: STEP 5 - TASK GENERATION")
    print("=" * 70)

    # File paths
    summaries_file = "data/decision_summaries/meeting1_decisions.json"
    transcript_file = "data/processed_transcripts/meeting1.json"
    tasks_file = "data/tasks/meeting1_tasks.json"

    # ── Load inputs ─────────────────────────────────────────────────────
    print("\n[1] LOADING INPUTS")
    print("-" * 70)

    summaries = load_summaries(summaries_file)
    print(f"✓ Loaded {len(summaries)} decision summaries")

    transcript = load_transcript(transcript_file)
    print(f"✓ Loaded {len(transcript)} transcript sentences")

    print(f"\nDecision summaries to convert:")
    for s in summaries:
        sids = ", ".join(str(sid) for sid in s["evidence_sentences"])
        print(f"  Cluster {s['cluster_id']}: \"{s['summary']}\" (evidence: [{sids}])")

    # ── Generate tasks ──────────────────────────────────────────────────
    print("\n\n[2] GENERATING TASKS (ML Extraction)")
    print("-" * 70)

    tasks = generate_tasks_from_transcript(
        summaries_path=summaries_file,
        transcript_path=transcript_file,
        output_path=tasks_file,
    )

    # ── Display results ─────────────────────────────────────────────────
    print("\n\n[3] GENERATED TASKS")
    print("-" * 70)

    for task in tasks:
        sids = ", ".join(str(sid) for sid in task["evidence_sentences"])
        print(f"\n  Task #{task['task_id']}:")
        print(f"    Title:       {task['title']}")
        print(f"    Assignee:    {task['assignee']}")
        print(f"    Deadline:    {task['deadline'] if task['deadline'] else 'None'}")
        print(f"    Evidence:    [{sids}]")
        print(f"    Cluster ID:  {task['cluster_id']}")

    # ── Quality analysis ────────────────────────────────────────────────
    print("\n\n[4] QUALITY ANALYSIS")
    print("-" * 70)

    issues = []
    for task in tasks:
        tid = task["task_id"]

        # Title must not be empty
        if not task["title"] or not task["title"].strip():
            issues.append(f"  Task {tid}: Empty title")

        # Title should not end with period (already stripped)
        if task["title"].endswith("."):
            issues.append(f"  Task {tid}: Title ends with period")

        # Assignee must not be empty
        if not task["assignee"] or not task["assignee"].strip():
            issues.append(f"  Task {tid}: Missing assignee")

        # Evidence must be preserved
        if not task["evidence_sentences"]:
            issues.append(f"  Task {tid}: No evidence sentences")

        # Required fields
        for field in ["task_id", "title", "assignee", "deadline",
                       "evidence_sentences", "cluster_id"]:
            if field not in task:
                issues.append(f"  Task {tid}: Missing field '{field}'")

    if issues:
        print("  ⚠ Quality issues found:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("  ✓ All tasks pass quality checks")

    # ── Statistics ──────────────────────────────────────────────────────
    print("\n\n[5] STATISTICS")
    print("-" * 70)

    assigned = sum(1 for t in tasks if t["assignee"] and t["assignee"] != "Unknown")
    with_deadline = sum(1 for t in tasks if t["deadline"])
    total_evidence = sum(len(t["evidence_sentences"]) for t in tasks)
    unique_assignees = set(t["assignee"] for t in tasks if t["assignee"])

    print(f"  Total summaries:         {len(summaries)}")
    print(f"  Total tasks:             {len(tasks)}")
    print(f"  Match (1:1):             {'✓' if len(summaries) == len(tasks) else '✗'}")
    print(f"  With assignee:           {assigned}/{len(tasks)}")
    print(f"  With deadline:           {with_deadline}/{len(tasks)}")
    print(f"  Total evidence links:    {total_evidence}")
    print(f"  Unique assignees:        {', '.join(sorted(unique_assignees))}")

    print("\n" + "=" * 70)
    print(f"✓ Step 5 complete: {len(tasks)} structured tasks generated")
    print(f"  Output: {tasks_file}")
    print("  Ready for STEP 6 (Display on Board)")
    print("=" * 70)


if __name__ == "__main__":
    main()
