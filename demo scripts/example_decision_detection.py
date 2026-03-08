"""
Example usage of the decision detection module (STEP 2).

Demonstrates:
1. Loading preprocessed transcript from STEP 1
2. Initializing transformer-based decision detector
3. Classifying sentences to identify decisions
4. Saving decision candidates for downstream clustering
5. Analyzing detection results
"""

from pipeline.decision_detector import (
    DecisionDetector,
    load_processed_transcript,
    save_decision_sentences,
    detect_decisions_in_transcript
)


def main():
    """Run decision detection on preprocessed transcript."""
    
    print("=" * 70)
    print("NLP PIPELINE: STEP 2 - DECISION DETECTION")
    print("=" * 70)
    
    # File paths
    preprocessed_file = "data/processed_transcripts/meeting1.json"
    decisions_file = "data/decision_sentences/meeting1_decisions.json"
    
    print("\n[1] DETECTING DECISION-RELATED SENTENCES")
    print("-" * 70)
    
    # Run full detection pipeline
    decisions = detect_decisions_in_transcript(
        input_path=preprocessed_file,
        output_path=decisions_file,
        threshold=0.6
    )
    
    print("\n[2] DECISION DETECTION RESULTS")
    print("-" * 70)
    
    if decisions:
        print(f"\nFirst 5 detected decisions:\n")
        for i, decision in enumerate(decisions[:5], 1):
            print(f"Decision #{i}")
            print(f"  ID:         {decision['sentence_id']}")
            print(f"  Speaker:    {decision['speaker']}")
            print(f"  Text:       {decision['text']}")
            print(f"  Confidence: {decision['decision_probability']:.1%}")
            print()
        
        if len(decisions) > 5:
            print(f"... and {len(decisions) - 5} more decisions\n")
    
    print("[3] DETECTION STATISTICS")
    print("-" * 70)
    
    # Load original sentences for comparison
    original_sentences = load_processed_transcript(preprocessed_file)
    
    detection_rate = len(decisions) / len(original_sentences) * 100
    
    print(f"\n  Total sentences: {len(original_sentences)}")
    print(f"  Decisions found: {len(decisions)}")
    print(f"  Detection rate: {detection_rate:.1f}%")
    
    # Group by speaker
    speaker_counts = {}
    for decision in decisions:
        speaker = decision['speaker']
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print(f"\n  Decisions by speaker:")
    for speaker in sorted(speaker_counts.keys()):
        count = speaker_counts[speaker]
        print(f"    {speaker}: {count} decision{'s' if count != 1 else ''}")
    
    # Confidence distribution
    confidences = [d['decision_probability'] for d in decisions]
    if confidences:
        print(f"\n  Confidence stats:")
        print(f"    Min:  {min(confidences):.1%}")
        print(f"    Max:  {max(confidences):.1%}")
        print(f"    Mean: {sum(confidences) / len(confidences):.1%}")
    
    print("\n[4] METHODOLOGICAL NOTES")
    print("-" * 70)
    print("""
  This classifier uses pretrained DistilBERT without fine-tuning.
  Therefore, detected decisions reflect general understanding of
  decisions in English text, not specifically trained on meeting data.
  
  Known limitations:
  • Suggestions vs Decisions: ambiguous phrases included as candidates
  • Backchannel responses: must be learned by model, not filtered
  • Context dependency: sentences lack surrounding context
  • Class imbalance: most sentences are not decisions (mitigated by threshold)
  
  These candidates are refined in subsequent pipeline steps:
  1. Clustering groups semantically related decisions
  2. Summarization creates concise action summaries
  3. Task generation converts summaries to actionable items
""")
    
    print("[5] OUTPUT")
    print("-" * 70)
    print(f"\n  ✓ Decision sentences saved to: {decisions_file}")
    print(f"  ✓ Ready for STEP 3 (clustering)")
    
    print("\n" + "=" * 70)
    print("✓ Step 2 complete: Decision detection finished")
    print("=" * 70)


if __name__ == "__main__":
    main()
