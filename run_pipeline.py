#!/usr/bin/env python3
"""
run_pipeline.py — NLP Action Extraction Pipeline (Refactored)

Runs the modular meeting action extraction pipeline on a transcript file.

Usage:
    python run_pipeline.py <transcript_file>
    python run_pipeline.py transcripts/sample_meeting_1.txt
    python run_pipeline.py                # paste from stdin
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict

# Apple Silicon safety
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from pipeline.config import OUTPUT_DATA_DIR, PROCESSED_DATA_DIR
from pipeline.preprocessing import parse_speakers, split_sentences, clean_sentences, filter_stopwords, resolve_triplets
from pipeline.preprocessing.cleaner import flag_sentence_types
from pipeline.detection import HybridDetector
from pipeline.detection.enhanced_features import detect_meeting_type
from pipeline.extraction import AssigneeExtractor, DeadlineExtractor
from pipeline.postprocessing import TaskBuilder, ConfidenceScorer, Deduplicator, TaskValidator


def load_transcript_from_file(path: Path) -> str:
    """Load transcript from file."""
    if not path.exists():
        print(f"✗ Transcript file not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def load_transcript_from_stdin() -> str:
    """Read transcript from stdin."""
    print("Paste meeting transcript below (CTRL+D on Mac/Linux; CTRL+Z+Enter on Windows):")
    print("-" * 70)
    try:
        text = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    
    if not text.strip():
        print("✗ Empty transcript.")
        sys.exit(1)
    
    return text


def save_step_output(meeting_id: str, step: int, data: List[Dict], description: str) -> Path:
    """Save output for each pipeline step to data folder."""
    if step == 1:
        # Preprocessing output
        output_file = PROCESSED_DATA_DIR / f"{meeting_id}.json"
    elif step == 2:
        # Decision detection output
        output_file = PROCESSED_DATA_DIR / f"{meeting_id}_decisions.json"
    elif step == 3:
        # Metadata extraction output
        output_file = PROCESSED_DATA_DIR / f"{meeting_id}_extractions.json"
    elif step == 4:
        # Final tasks output
        output_file = OUTPUT_DATA_DIR / f"{meeting_id}_tasks.json"
    else:
        return None
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove non-serializable fields (spacy_doc, etc.) before saving
    def make_serializable(item):
        """Remove spacy_doc and other non-JSON-serializable fields."""
        if not isinstance(item, dict):
            return item
        clean_item = {}
        for key, value in item.items():
            # Skip non-serializable types
            if key in ("spacy_doc",):
                continue
            # Only keep JSON-serializable types
            if isinstance(value, (str, int, float, bool, type(None))):
                clean_item[key] = value
            elif isinstance(value, dict):
                clean_item[key] = make_serializable(value)
            elif isinstance(value, list):
                clean_item[key] = [
                    make_serializable(v) if isinstance(v, dict) else v
                    for v in value
                ]
        return clean_item
    
    clean_data = [make_serializable(item) if isinstance(item, dict) else item for item in data]
    
    with open(output_file, 'w') as f:
        json.dump(clean_data, f, indent=2)
    
    print(f"    [*] {description}: {output_file}")
    return output_file


def main():
    """Main entry point - processes transcript through all pipeline steps and saves each step's output."""
    start = time.time()
    
    # ── Load transcript ─────────────────────────────────────────────────
    if len(sys.argv) >= 2:
        transcript_path = Path(sys.argv[1])
        raw_text = load_transcript_from_file(transcript_path)
        meeting_id = transcript_path.stem  # Extract filename without extension
        print(f"\n[*] Loaded: {transcript_path}")
    else:
        raw_text = load_transcript_from_stdin()
        meeting_id = "meeting"
        print(f"\n[*] Loaded from stdin")
    
    line_count = len([l for l in raw_text.strip().splitlines() if l.strip()])
    char_count = len(raw_text)
    print(f"    Lines: {line_count} | Characters: {char_count}")
    
    print("\n" + "="*60)
    print("  NLP ACTION EXTRACTION PIPELINE")
    print("="*60)
    
    # ── STEP 1: PREPROCESSING ────────────────────────────────────────
    print("\n[1/4] PREPROCESSING")
    print("-" * 60)
    
    speaker_utterances = parse_speakers(raw_text)
    print(f"    * Parsed {len(speaker_utterances)} speaker utterances")
    
    # Extract known speakers for downstream use
    known_speakers = set(s.get("speaker", "") for s in speaker_utterances if s.get("speaker"))
    print(f"    * Known speakers: {', '.join(sorted(known_speakers))}")
    
    sentences = split_sentences(speaker_utterances)
    print(f"    * Split into {len(sentences)} sentences")
    
    pre_clean_count = len(sentences)
    sentences = clean_sentences(sentences)
    print(f"    * Cleaned sentences (removed empty)")
    
    pre_filter_count = len(sentences)
    sentences = filter_stopwords(sentences)
    filtered_count = pre_filter_count - len(sentences)
    print(f"    * Filtered {filtered_count} stopword sentences")
    
    sentences = resolve_triplets(sentences, known_speakers=known_speakers)
    print(f"    * Resolved triplets and scored confidence")
    
    # Flag sentence types (observation, consequence, metric, general)
    sentences = flag_sentence_types(sentences)
    print(f"    * Flagged sentence types")
    
    # Detect meeting type (task_oriented, status_review, mixed)
    meeting_type = detect_meeting_type(sentences)
    print(f"    * Meeting type: {meeting_type}")
    
    # Save Step 1: Preprocessed sentences
    save_step_output(meeting_id, 1, sentences, "Preprocessing output saved to")
    
    # ── STEP 2: DECISION DETECTION ────────────────────────────────────
    print("\n[2/4] DECISION DETECTION")
    print("-" * 60)
    print("[*] Loading zero-shot classification model...")
    
    # Initialize detector with enhanced features
    # Features: dependency tree modals, context window, semantic features
    detector = HybridDetector(
        use_transformer=True,
        use_features=True,  # Enable modal verbs and direct object detection
        use_context=True,   # Enable context window (prior 2 sentences)
        context_window=2
    )
    
    # Initialize extractors with known speakers
    assignee_extractor = AssigneeExtractor()
    assignee_extractor.set_known_speakers(known_speakers)
    deadline_extractor = DeadlineExtractor()
    print("[+] QA model loaded")
    print("[+] spaCy NER model loaded")
    
    detected = detector.detect_batch(sentences, meeting_type=meeting_type)
    decision_sentences = [s for s in detected if s.get("is_decision")]
    print(f"    * Detected {len(decision_sentences)} decision sentences")
    
    if decision_sentences:
        avg_conf = sum(s.get('confidence', 0) for s in decision_sentences) / len(decision_sentences)
        print(f"    * Confidence scores: avg={avg_conf:.2f}")
        
        # Show modal boost statistics
        with_modal = sum(1 for s in decision_sentences if s.get("modal_boost", 0) > 0)
        if with_modal > 0:
            avg_boost = sum(s.get("modal_boost", 0) for s in decision_sentences) / len(decision_sentences)
            print(f"    * Modal verbs detected: {with_modal}/{len(decision_sentences)} (avg boost: {avg_boost:.2f})")
    
    # Save Step 2: Detected decisions
    save_step_output(meeting_id, 2, detected, "Decision detection output saved to")
    
    if not decision_sentences:
        print(f"    [!] No decisions detected in {meeting_id}")
        return 1
    
    # ── STEP 3: METADATA EXTRACTION ──────────────────────────────────────
    print("\n[3/4] METADATA EXTRACTION")
    print("-" * 60)
    
    task_definitions = []
    for sent in decision_sentences:
        text = sent.get("text", "")
        
        # Extract assignee
        assignee = assignee_extractor.extract([sent])
        
        # Extract deadline
        deadline = deadline_extractor.extract(text)
        
        # Store extraction (description will be generated during task building)
        task_definitions.append({
            "raw_text": text,  # Raw text for description generation in postprocessing
            "assignee": assignee,
            "deadline": deadline,
            "confidence": sent.get("confidence", 0.8),
            "root_verb": sent.get("root_verb"),  # For triplet-based titles
            "object": sent.get("object"),  # For triplet-based titles
            "evidence": {
                    "text": text,
                    "speaker": sent.get("speaker", "Unknown"),
                    "sentence_type": sent.get("sentence_type", "general"),
                    "hard_filtered": sent.get("hard_filtered", False),
                }
            })
    
    print(f"    * Generated {len(task_definitions)} task definitions")
    print(f"    * With assignees: {sum(1 for t in task_definitions if t.get('assignee'))}")
    print(f"    * With deadlines: {sum(1 for t in task_definitions if t.get('deadline'))}")
    
    # Save Step 3: Extracted metadata
    save_step_output(meeting_id, 3, task_definitions, "Extraction output saved to")
    
    # ── STEP 4: POSTPROCESSING ───────────────────────────────────────
    print("\n[4/4] POSTPROCESSING")
    print("-" * 60)
    
    # Build tasks
    tasks = TaskBuilder.build_batch(task_definitions)
    print(f"    * Built {len(tasks)} task objects")
    
    # Score confidence
    tasks = ConfidenceScorer.score_batch(tasks)
    
    # Add manual review flags for borderline confidence
    tasks = TaskValidator.add_manual_review_flags(tasks)
    
    # Filter invalid tasks (metrics, reactions, etc.)
    before_validation = len(tasks)
    tasks = TaskValidator.filter_batch(tasks, meeting_type=meeting_type)
    print(f"    * Validated tasks: {before_validation} → {len(tasks)} (removed {before_validation - len(tasks)})")
    
    # Deduplicate
    tasks = Deduplicator.deduplicate(tasks)
    print(f"    * After deduplication: {len(tasks)} unique tasks")
    
    # Save Step 4: Final tasks
    save_step_output(meeting_id, 4, tasks, "Tasks output saved to")
    
    elapsed = time.time() - start
    
    # ── SUMMARY ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  SUMMARY: Extracted {len(tasks)} action items")
    print("="*60)
    print(f"[*] Completed in: {elapsed:.1f}s")
    
    # ── Display results ──────────────────────────────────────────────
    if tasks:
        print(f"\n{'='*70}")
        print(f"  EXTRACTED {len(tasks)} TASK(S)")
        print(f"{'='*70}")
        
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. {task['task']}")
            
            if task.get('assignee'):
                print(f"   Assignee: {task['assignee']}")
            
            if task.get('deadline'):
                print(f"   Deadline: {task['deadline']}")
            
            if task.get('confidence'):
                conf_pct = f"{task['confidence']*100:.0f}%"
                print(f"   Confidence: {conf_pct}")
            
            if task.get('evidence'):
                evidence = task['evidence']
                if evidence.get('speaker'):
                    print(f"   Speaker: {evidence['speaker']}")
    else:
        print(f"\n[!] No tasks extracted from transcript.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
