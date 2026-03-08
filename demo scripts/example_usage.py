"""
Example usage of the transcript preprocessing module.

This script demonstrates:
1. Loading a raw transcript
2. Preprocessing it with spaCy sentence segmentation
3. Saving the structured output as JSON
"""

from pipeline.preprocess import (
    preprocess_transcript,
    save_processed_transcript,
    load_raw_transcript
)


def main():
    """Run preprocessing pipeline on example transcript."""
    
    print("=" * 60)
    print("NLP PIPELINE: STEP 1 - TRANSCRIPT PREPROCESSING")
    print("=" * 60)
    
    # Load raw transcript
    print("\n[1] Loading raw transcript...")
    raw_transcript = load_raw_transcript("data/raw_transcripts/meeting1.txt")
    print(f"✓ Loaded {len(raw_transcript)} characters")
    print("\nRaw transcript preview:")
    print("-" * 60)
    print(raw_transcript[:300] + "...")
    
    # Preprocess transcript
    print("\n[2] Preprocessing with spaCy sentence segmentation...")
    sentences = preprocess_transcript(raw_transcript)
    print(f"✓ Extracted {len(sentences)} sentences")
    
    # Display structured output
    print("\n[3] Structured sentence-level dataset:")
    print("-" * 60)
    for sentence in sentences[:5]:  # Show first 5
        print(f"  ID: {sentence['sentence_id']}")
        print(f"  Speaker: {sentence['speaker']}")
        print(f"  Text: {sentence['text']}")
        print()
    
    if len(sentences) > 5:
        print(f"  ... ({len(sentences) - 5} more sentences)")
    
    # Save to JSON
    print("\n[4] Saving to JSON...")
    output_path = "data/processed_transcripts/meeting1.json"
    save_processed_transcript(sentences, output_path)
    
    # Summary statistics
    speakers = set(s['speaker'] for s in sentences)
    print("\n[5] Summary Statistics:")
    print(f"  Total speakers: {len(speakers)}")
    print(f"  Speakers: {', '.join(sorted(speakers))}")
    print(f"  Total sentences: {len(sentences)}")
    print(f"  Avg sentences per speaker: {len(sentences) / len(speakers):.1f}")
    
    print("\n" + "=" * 60)
    print("✓ Step 1 complete: Transcript preprocessed and ready for")
    print("  downstream components (decision detection, clustering)")
    print("=" * 60)


if __name__ == "__main__":
    main()
