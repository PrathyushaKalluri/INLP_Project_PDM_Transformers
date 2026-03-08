"""
Tests for the decision summarization module (STEP 4).

Tests cover:
- Single-sentence cleaning (conversational prefix removal)
- Multi-sentence summarization (fallback to best-sentence selection)
- Filler word removal
- Pronoun resolution
- Proper noun and date capitalization
- Edge cases (empty input, punctuation, question marks)
- Output structure validation
- Integration with STEP 3 cluster format
"""

import json
import os
import tempfile
from pathlib import Path

# ── Apple Silicon safety ────────────────────────────────────────────────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pipeline.summarization import (
    DecisionSummarizer,
    load_clusters,
    save_summaries,
    summarize_decisions_in_transcript,
    CONVERSATIONAL_PATTERNS,
    FILLER_WORDS,
    DAYS_OF_WEEK,
    MONTHS,
)


def make_cluster(cluster_id, sentences, texts, speakers=None):
    """Helper to build a cluster dict."""
    if speakers is None:
        speakers = ["A"] * len(texts)
    return {
        "cluster_id": cluster_id,
        "sentences": sentences,
        "texts": texts,
        "speakers": speakers,
    }


def main():
    print("=" * 70)
    print("STEP 4: DECISION SUMMARIZATION — TEST SUITE")
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

    # ── Initialize summarizer (model may or may not load) ───────────────
    print("\n[1] INITIALIZING SUMMARIZER")
    print("-" * 70)

    summarizer = DecisionSummarizer()
    model_available = summarizer._model is not None
    print(f"  Model available: {model_available}")
    print(f"  (Tests work with or without model)\n")

    # ── Test: Conversational prefix removal ─────────────────────────────
    print("\n[2] CONVERSATIONAL PREFIX REMOVAL")
    print("-" * 70)

    prefix_tests = [
        ("I think we should focus on the API", "Focus on the API."),
        ("we should focus on the API", "Focus on the API."),
        ("we need to deploy the system", "Deploy the system."),
        ("we have to finish the report", "Finish the report."),
        ("let's aim for next week", "Aim for next week."),
        ("let's finalize this", "Finalize the task."),
        ("can you prepare the spec?", "Prepare the spec."),
        ("could you review the code?", "Review the code."),
        ("I will prepare the documentation", "Prepare the documentation."),
        ("I will also prepare the documentation", "Prepare the documentation."),
        ("I'll handle the deployment", "Handle the deployment."),
        ("I am going to write the tests", "Write the tests."),
        ("maybe we should reconsider", "Reconsider."),
        ("maybe reconsider the design", "Reconsider the design."),
        ("please update the dashboard", "Update the dashboard."),
        ("also we need to fix the bug", "Fix the bug."),
        ("also we should review the PR", "Review the PR."),
        ("also check the logs", "Check the logs."),
        ("I think we need to refactor", "Refactor."),
    ]

    for raw, expected in prefix_tests:
        result = summarizer._clean_to_task_statement(raw)
        check(
            f"\"{raw[:45]}...\" → \"{result}\"",
            result == expected,
            f"Expected \"{expected}\", got \"{result}\"",
        )

    # ── Test: Filler word removal ───────────────────────────────────────
    print("\n[3] FILLER WORD REMOVAL")
    print("-" * 70)

    filler_tests = [
        ("I think we should focus on the payment API first",
         "Focus on the payment API."),
        ("we should just deploy it tomorrow",
         "Deploy the system tomorrow."),
        ("we need to actually finish the report",
         "Finish the report."),
    ]

    for raw, expected in filler_tests:
        result = summarizer._clean_to_task_statement(raw)
        check(
            f"\"{raw[:45]}...\" → \"{result}\"",
            result == expected,
            f"Expected \"{expected}\", got \"{result}\"",
        )

    # ── Test: Pronoun resolution ────────────────────────────────────────
    print("\n[4] PRONOUN RESOLUTION")
    print("-" * 70)

    pronoun_tests = [
        ("we need to deploy it by end of march",
         "Deploy the system by end of March."),
        ("we should ship it next week",
         "Ship the system next week."),
    ]

    for raw, expected in pronoun_tests:
        result = summarizer._clean_to_task_statement(raw)
        check(
            f"\"{raw[:45]}...\" → \"{result}\"",
            result == expected,
            f"Expected \"{expected}\", got \"{result}\"",
        )

    # ── Test: Date and day capitalization ───────────────────────────────
    print("\n[5] DATE/DAY CAPITALIZATION")
    print("-" * 70)

    date_tests = [
        ("let's aim for next wednesday", "Aim for next Wednesday."),
        ("we need to deploy it by end of march",
         "Deploy the system by end of March."),
        ("let's meet on friday", "Meet on Friday."),
        ("deploy by january", "Deploy by January."),
    ]

    for raw, expected in date_tests:
        result = summarizer._clean_to_task_statement(raw)
        check(
            f"\"{raw[:45]}...\" → \"{result}\"",
            result == expected,
            f"Expected \"{expected}\", got \"{result}\"",
        )

    # ── Test: Punctuation handling ──────────────────────────────────────
    print("\n[6] PUNCTUATION HANDLING")
    print("-" * 70)

    punct_tests = [
        ("can you prepare the spec?", "Prepare the spec."),
        ("we need to deploy it by end of march.",
         "Deploy the system by end of March."),
        ("focus on the API", "Focus on the API."),
    ]

    for raw, expected in punct_tests:
        result = summarizer._clean_to_task_statement(raw)
        check(
            f"\"{raw[:45]}...\" → \"{result}\"",
            result == expected,
            f"Expected \"{expected}\", got \"{result}\"",
        )

    # ── Test: Single-sentence cluster summarization ─────────────────────
    print("\n[7] SINGLE-SENTENCE CLUSTER SUMMARIZATION")
    print("-" * 70)

    single_tests = [
        (
            make_cluster(0, [4], ["I think we should focus on the payment API first"]),
            "Focus on the payment API.",
        ),
        (
            make_cluster(1, [18], ["let's aim for next wednesday"]),
            "Aim for next Wednesday.",
        ),
        (
            make_cluster(2, [6], ["we need to deploy it by end of march."]),
            "Deploy the system by end of March.",
        ),
        (
            make_cluster(3, [15], ["I will also prepare the documentation"]),
            "Prepare the documentation.",
        ),
        (
            make_cluster(4, [7], ["can you prepare the technical spec?"]),
            "Prepare the technical spec.",
        ),
    ]

    for cluster, expected in single_tests:
        result = summarizer.summarize_cluster(cluster)
        check(
            f"Cluster {cluster['cluster_id']}: \"{result['summary']}\"",
            result["summary"] == expected,
            f"Expected \"{expected}\", got \"{result['summary']}\"",
        )

    # ── Test: Multi-sentence cluster summarization ──────────────────────
    print("\n[8] MULTI-SENTENCE CLUSTER SUMMARIZATION")
    print("-" * 70)

    multi_cluster = make_cluster(
        0,
        [4, 9],
        [
            "I think we should focus on the payment API first",
            "also we need to finalize the pricing model",
        ],
        ["B", "B"],
    )
    result = summarizer.summarize_cluster(multi_cluster)

    # The summary should be one concise sentence, not a broken concatenation
    check(
        "Multi-sentence produces one clean sentence",
        ". " not in result["summary"].rstrip("."),
        f"Got: \"{result['summary']}\"",
    )
    check(
        "Multi-sentence summary doesn't contain conversational words",
        not any(
            marker.lower() in result["summary"].lower()
            for marker in ["I think", "we should", "we need to", "also"]
        ),
        f"Got: \"{result['summary']}\"",
    )
    check(
        "Multi-sentence preserves evidence IDs",
        result["evidence_sentences"] == [4, 9],
    )

    # ── Test: Output structure ──────────────────────────────────────────
    print("\n[9] OUTPUT STRUCTURE VALIDATION")
    print("-" * 70)

    test_cluster = make_cluster(99, [10, 20], ["prepare the spec", "review the PR"])
    result = summarizer.summarize_cluster(test_cluster)

    check("Has cluster_id", "cluster_id" in result)
    check("Has summary", "summary" in result)
    check("Has evidence_sentences", "evidence_sentences" in result)
    check("cluster_id is int", isinstance(result["cluster_id"], int))
    check("summary is str", isinstance(result["summary"], str))
    check("evidence_sentences is list", isinstance(result["evidence_sentences"], list))
    check("cluster_id matches", result["cluster_id"] == 99)
    check("evidence_sentences preserved", result["evidence_sentences"] == [10, 20])

    # ── Test: Batch summarization (1:1 cluster→summary) ─────────────────
    print("\n[10] BATCH SUMMARIZATION (1:1 MAPPING)")
    print("-" * 70)

    clusters = [
        make_cluster(0, [1], ["we should deploy tomorrow"]),
        make_cluster(1, [2], ["can you review the PR?"]),
        make_cluster(2, [3, 4], ["prepare the report", "finalize the budget"]),
    ]

    summaries = summarizer.summarize_clusters(clusters)
    check(
        f"Number of summaries ({len(summaries)}) == clusters ({len(clusters)})",
        len(summaries) == len(clusters),
    )

    for i, (cluster, summary) in enumerate(zip(clusters, summaries)):
        check(
            f"Cluster {i}: cluster_id matches",
            summary["cluster_id"] == cluster["cluster_id"],
        )
        check(
            f"Cluster {i}: evidence IDs match",
            summary["evidence_sentences"] == cluster["sentences"],
        )

    # ── Test: I/O helpers ───────────────────────────────────────────────
    print("\n[11] I/O HELPERS (load / save)")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save test clusters
        cluster_path = os.path.join(tmpdir, "clusters.json")
        test_clusters = [
            make_cluster(0, [1], ["we should deploy tomorrow"]),
            make_cluster(1, [2], ["prepare the documentation"]),
        ]
        with open(cluster_path, "w") as f:
            json.dump(test_clusters, f)

        # Load clusters
        loaded = load_clusters(cluster_path)
        check("load_clusters reads correct count", len(loaded) == 2)
        check("load_clusters preserves structure", loaded[0]["cluster_id"] == 0)

        # Save summaries
        summary_path = os.path.join(tmpdir, "sub", "summaries.json")
        test_summaries = [
            {"cluster_id": 0, "summary": "Deploy tomorrow.", "evidence_sentences": [1]},
        ]
        save_summaries(test_summaries, summary_path)
        check("save_summaries creates file", os.path.exists(summary_path))
        check(
            "save_summaries creates parent dirs",
            os.path.exists(os.path.join(tmpdir, "sub")),
        )

        with open(summary_path, "r") as f:
            reloaded = json.load(f)
        check("save_summaries correct content", reloaded[0]["summary"] == "Deploy tomorrow.")

    # ── Test: End-to-end with real data ─────────────────────────────────
    print("\n[12] END-TO-END WITH REAL DATA")
    print("-" * 70)

    real_cluster_path = "data/decision_clusters/meeting1_clusters.json"
    if os.path.exists(real_cluster_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "meeting1_decisions.json")
            summaries = summarize_decisions_in_transcript(
                input_path=real_cluster_path,
                output_path=output_path,
            )

            real_clusters = load_clusters(real_cluster_path)
            check(
                f"Real data: {len(summaries)} summaries for {len(real_clusters)} clusters",
                len(summaries) == len(real_clusters),
            )
            check("Real data: output file created", os.path.exists(output_path))

            # Verify all summaries are well-formed
            for s in summaries:
                check(
                    f"Real Cluster {s['cluster_id']}: ends with period",
                    s["summary"].endswith("."),
                    f"Got: \"{s['summary']}\"",
                )
                check(
                    f"Real Cluster {s['cluster_id']}: starts with capital",
                    s["summary"][0].isupper(),
                    f"Got: \"{s['summary']}\"",
                )
                check(
                    f"Real Cluster {s['cluster_id']}: no internal periods",
                    ". " not in s["summary"].rstrip("."),
                    f"Got: \"{s['summary']}\"",
                )
    else:
        print(f"  ⚠ Skipping: {real_cluster_path} not found")
        print("    Run STEP 3 first to generate cluster data")

    # ── Test: Edge cases ────────────────────────────────────────────────
    print("\n[13] EDGE CASES")
    print("-" * 70)

    # Empty text
    result = summarizer._clean_to_task_statement("")
    check("Empty string → empty", result == "")

    # Whitespace only
    result = summarizer._clean_to_task_statement("   ")
    check("Whitespace only → empty", result == "")

    # Already clean
    result = summarizer._clean_to_task_statement("Deploy the system.")
    check("Already clean → unchanged", result == "Deploy the system.")

    # All prefixes stripped leaving nothing meaningful
    result = summarizer._clean_to_task_statement("I think we should")
    check("Only prefix → empty or minimal", result == "" or len(result) <= 2)

    # No clusters
    empty_result = summarizer.summarize_clusters([])
    check("Empty cluster list → empty result", empty_result == [])

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
