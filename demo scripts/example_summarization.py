"""
Example usage of the decision summarization module (STEP 4).

Demonstrates:
1. Loading decision clusters from STEP 3
2. Initializing the hybrid summarizer (model + rule-based)
3. Generating concise decision summaries
4. Saving structured summaries for downstream task generation
5. Analyzing summary quality
"""

from pipeline.summarization import (
    DecisionSummarizer,
    load_clusters,
    save_summaries,
    summarize_decisions_in_transcript,
)


def main():
    """Run decision summarization on clustered decisions."""

    print("=" * 70)
    print("NLP PIPELINE: STEP 4 - DECISION SUMMARIZATION")
    print("=" * 70)

    # File paths
    clusters_file = "data/decision_clusters/meeting1_clusters.json"
    summaries_file = "data/decision_summaries/meeting1_decisions.json"

    print("\n[1] LOADING DECISION CLUSTERS (from STEP 3)")
    print("-" * 70)

    clusters = load_clusters(clusters_file)
    print(f"✓ Loaded {len(clusters)} clusters\n")

    for cluster in clusters:
        cid = cluster["cluster_id"]
        n = len(cluster["texts"])
        sids = ", ".join(str(s) for s in cluster["sentences"])
        print(f"  Cluster {cid}: {n} sentence(s), sentence IDs [{sids}]")
        for text in cluster["texts"]:
            print(f"    → \"{text}\"")
        print()

    print("\n[2] GENERATING DECISION SUMMARIES")
    print("-" * 70)

    # Run full summarization pipeline
    summaries = summarize_decisions_in_transcript(
        input_path=clusters_file,
        output_path=summaries_file,
    )

    print("\n[3] DECISION SUMMARY RESULTS")
    print("-" * 70)

    for summary in summaries:
        cid = summary["cluster_id"]
        sids = ", ".join(str(s) for s in summary["evidence_sentences"])
        print(f"\n  Cluster {cid}:")
        print(f"    Summary:   {summary['summary']}")
        print(f"    Evidence:  [{sids}]")

    print("\n\n[4] QUALITY ANALYSIS")
    print("-" * 70)

    # Check summary quality metrics
    issues = []
    for summary in summaries:
        text = summary["summary"]
        cid = summary["cluster_id"]

        # Must end with period
        if not text.endswith("."):
            issues.append(f"  Cluster {cid}: Missing trailing period")

        # Must start with capital letter
        if text and not text[0].isupper():
            issues.append(f"  Cluster {cid}: Does not start with capital letter")

        # Should be one sentence
        inner = text.rstrip(".")
        if "." in inner:
            issues.append(f"  Cluster {cid}: Contains multiple sentences")

        # Should not contain conversational words
        conversational_markers = [
            "I think", "we should", "maybe", "let's",
            "can you", "could you", "I will", "please",
        ]
        for marker in conversational_markers:
            if marker.lower() in text.lower():
                issues.append(
                    f"  Cluster {cid}: Contains conversational phrase \"{marker}\""
                )

    if issues:
        print("  ⚠ Quality issues found:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("  ✓ All summaries pass quality checks")

    # Statistics
    print("\n\n[5] STATISTICS")
    print("-" * 70)

    avg_len = sum(len(s["summary"]) for s in summaries) / len(summaries)
    total_evidence = sum(len(s["evidence_sentences"]) for s in summaries)

    print(f"  Total clusters:          {len(clusters)}")
    print(f"  Total summaries:         {len(summaries)}")
    print(f"  Match (1:1):             {'✓' if len(clusters) == len(summaries) else '✗'}")
    print(f"  Avg summary length:      {avg_len:.0f} chars")
    print(f"  Total evidence links:    {total_evidence}")

    print("\n" + "=" * 70)
    print(f"✓ Step 4 complete: {len(summaries)} decision summaries generated")
    print("  Output: data/decision_summaries/meeting1_decisions.json")
    print("  Ready for STEP 5 (Task Generation)")
    print("=" * 70)


if __name__ == "__main__":
    main()
