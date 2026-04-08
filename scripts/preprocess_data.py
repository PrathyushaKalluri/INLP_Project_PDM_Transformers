#!/usr/bin/env python3
"""
Preprocessing script to prepare raw data.

Converts raw transcripts to structured format matching meeting.json format.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.preprocessing import (
    parse_speakers,
    split_sentences,
    clean_sentences,
    filter_stopwords,
    normalize_to_meeting_format,
    post_process_metadata,
)
from pipeline.config import RAW_DATA_DIR, PROCESSED_DATA_DIR


def preprocess_file(input_path: Path, output_path: Path) -> None:
    """Preprocess a single transcript file."""
    print(f"Processing: {input_path}")
    
    with open(input_path, 'r') as f:
        transcript = f.read()
    
    # ── PREPROCESSING PIPELINE ────────────────────────────────────
    # Parse speakers (multi-format support)
    speaker_utterances = parse_speakers(transcript)
    print(f"  * Parsed {len(speaker_utterances)} speaker turns")
    
    # Split sentences (with metadata enrichment)
    sentences = split_sentences(speaker_utterances)
    print(f"  * Split into {len(sentences)} sentences")
    
    # Clean sentences (normalize whitespace + Indian English)
    sentences = clean_sentences(sentences)
    print(f"  * Cleaned sentences")
    
    # Filter stopwords (remove non-actionable sentences)
    sentences = filter_stopwords(sentences)
    print(f"  * Filtered stopwords: {len(sentences)} actionable sentences")
    
    # Normalize to meeting.json format (keep linguistic metadata)
    sentences = normalize_to_meeting_format(sentences, keep_metadata=True)
    
    # ── POST-PROCESSING ───────────────────────────────────────────────
    # Apply context-aware fixes for edge cases
    print(f"  * Post-processing metadata...")
    sentences = post_process_metadata(sentences)
    print(f"  * Applied 9 linguistic fixes (Let's, you-resolution, anaphora, etc.)")
    
    # ── SAVE ──────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(sentences, f, indent=2)
    
    print(f"  ✓ Saved to {output_path}\n")


def main():
    """Process all raw transcripts."""
    raw_files = list(RAW_DATA_DIR.glob("*.txt"))
    
    if not raw_files:
        print(f"No raw transcripts found in {RAW_DATA_DIR}")
        return 1
    
    print(f"Found {len(raw_files)} transcript(s)\n")
    
    for raw_file in raw_files:
        # Save to data/processed/ with meeting name (e.g., meeting1.json)
        output_file = PROCESSED_DATA_DIR / f"{raw_file.stem}.json"
        try:
            preprocess_file(raw_file, output_file)
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
