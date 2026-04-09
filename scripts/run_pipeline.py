#!/usr/bin/env python3
"""
Main script to run the NLP action extraction pipeline.

Usage:
    python run_pipeline.py <transcript_file>
    python run_pipeline.py transcripts/meeting.txt
"""

import sys
import json
from pathlib import Path

# Add parent directory to path so we can import pipeline
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import run_pipeline
from pipeline.config import OUTPUT_DATA_DIR


def main():
    """Load transcript and run pipeline."""
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <transcript_file>")
        print("Example: python run_pipeline.py transcripts/sample_meeting_1.txt")
        sys.exit(1)
    
    transcript_path = Path(sys.argv[1])
    
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)
    
    print(f"\n📄 Loading transcript: {transcript_path}")
    
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    print(f"📄 Transcript loaded ({len(transcript)} characters)")
    
    # Run pipeline
    tasks = run_pipeline(transcript)
    
    # Save output
    output_file = OUTPUT_DATA_DIR / "tasks.json"
    with open(output_file, 'w') as f:
        json.dump(tasks, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Display results
    if tasks:
        print(f"\n📋 EXTRACTED TASKS:")
        print("-" * 60)
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. {task['task']}")
            if task.get('assignee'):
                print(f"   👤 Assignee: {task['assignee']}")
            if task.get('deadline'):
                print(f"   📅 Deadline: {task['deadline']}")
            if task.get('confidence'):
                print(f"   🎯 Confidence: {task['confidence']:.2%}")
    else:
        print("\n[!] No tasks extracted from transcript")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
