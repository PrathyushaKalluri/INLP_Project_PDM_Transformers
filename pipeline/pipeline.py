"""Main NLP action extraction pipeline."""

from typing import List, Dict
from pathlib import Path

from .config import (
    USE_TRANSFORMER_CLASSIFIER,
    USE_RULE_BASED_DETECTION,
    OUTPUT_DATA_DIR,
)

from .preprocessing import parse_speakers, split_sentences, clean_sentences, filter_stopwords, resolve_triplets, flag_sentence_types
from .detection import HybridDetector
from .extraction import AssigneeExtractor, DeadlineExtractor
from .postprocessing import TaskBuilder, ConfidenceScorer, Deduplicator, TaskValidator


class NLPActionExtractor:
    """
    Main pipeline orchestrator for extracting action items from meeting transcripts.
    
    Workflow:
    1. Preprocessing: Parse speakers, split sentences, clean text
    2. Detection: Identify decision-related sentences (rule-based + transformer)
    3. Extraction: Extract assignee, deadline (description generated in postprocessing)
    4. Postprocessing: Build tasks, score confidence, remove duplicates
    """
    
    def __init__(self):
        """Initialize pipeline components."""
        self.detector = HybridDetector(use_transformer=USE_TRANSFORMER_CLASSIFIER)
        self.assignee_extractor = AssigneeExtractor()
        self.deadline_extractor = DeadlineExtractor()
        self.meeting_type = "mixed"  # Will be set during pipeline run
        self.known_speakers: set = set()  # Will be populated during preprocessing
        print("[+] Pipeline initialized")
    
    def run_pipeline(self, transcript: str) -> List[Dict]:
        """
        Execute full pipeline from raw transcript to structured tasks.
        
        Args:
            transcript (str): Raw meeting transcript with speaker labels
                            Format: "Speaker: utterance"
        
        Returns:
            list: Structured task objects
                 [
                     {
                         "task_id": str,
                         "task": str,
                         "assignee": str,
                         "deadline": str,
                         "confidence": float,
                         "evidence": {
                             "text": str,
                             "speaker": str
                         }
                     }
                 ]
        """
        print("\n" + "="*60)
        print("  NLP ACTION EXTRACTION PIPELINE")
        print("="*60)
        
        # ── STEP 1: PREPROCESSING ────────────────────────────────────────
        print("\n[1/4] PREPROCESSING")
        print("-" * 60)
        
        speaker_utterances = parse_speakers(transcript)
        print(f"    * Parsed {len(speaker_utterances)} speaker utterances")
        
        # Extract unique speakers for assignee extraction
        self.known_speakers = set(s.get("speaker", "") for s in speaker_utterances if s.get("speaker"))
        self.assignee_extractor.set_known_speakers(self.known_speakers)
        print(f"    * Known speakers: {', '.join(sorted(self.known_speakers))}")
        
        sentences = split_sentences(speaker_utterances)
        print(f"    * Split into {len(sentences)} sentences")
        
        sentences = clean_sentences(sentences)
        print(f"    * Cleaned sentences (removed empty)")
        
        sentences = filter_stopwords(sentences)
        total_filtered = len(speaker_utterances) + len(split_sentences(speaker_utterances)) - len(sentences)
        print(f"    * Filtered {total_filtered} stopword sentences")
        
        sentences = resolve_triplets(sentences)
        print(f"    * Resolved triplets and scored confidence")
        
        # NEW: Flag sentence types (observation, consequence, metric, general)
        sentences = flag_sentence_types(sentences)
        print(f"    * Flagged sentence types")
        
        # NEW: Detect meeting type (task_oriented, status_review, mixed)
        from .detection.enhanced_features import detect_meeting_type
        meeting_type = detect_meeting_type(sentences)
        print(f"    * Meeting type: {meeting_type}")
        
        # Store meeting type for downstream steps
        self.meeting_type = meeting_type
        
        # ── STEP 2: DETECTION ────────────────────────────────────────────
        print("\n[2/4] DECISION DETECTION")
        print("-" * 60)
        
        detected = self.detector.detect_batch(sentences, meeting_type=self.meeting_type)
        decision_sentences = [s for s in detected if s.get("is_decision")]
        print(f"    * Detected {len(decision_sentences)} decision sentences")
        if decision_sentences:
            avg_conf = sum(s.get('confidence', 0) for s in decision_sentences) / len(decision_sentences)
            print(f"    * Confidence scores: avg={avg_conf:.2f}")
        
        if not decision_sentences:
            print("    [!] No decisions detected in transcript")
            return []
        
        # ── STEP 3: EXTRACTION ───────────────────────────────────────────
        print("\n[3/4] METADATA EXTRACTION")
        print("-" * 60)
        
        task_definitions = []
        for sent in decision_sentences:
            text = sent.get("text", "")
            
            # Extract assignee
            assignee = self.assignee_extractor.extract([sent])
            
            # Extract deadline
            deadline = self.deadline_extractor.extract(text)
            
            # Store extraction with raw_text (description will be generated in postprocessing)
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
        
        # ── STEP 4: POSTPROCESSING ───────────────────────────────────────
        print("\n[4/4] POSTPROCESSING")
        print("-" * 60)
        
        # Build tasks (includes description generation)
        tasks = TaskBuilder.build_batch(task_definitions)
        print(f"    * Built {len(tasks)} task objects")
        
        # Score confidence
        tasks = ConfidenceScorer.score_batch(tasks)
        
        # NEW: Add manual review flags for borderline confidence
        tasks = TaskValidator.add_manual_review_flags(tasks)
        
        # NEW: Filter invalid tasks (metrics, reactions, etc.)
        before_validation = len(tasks)
        tasks = TaskValidator.filter_batch(tasks, meeting_type=self.meeting_type)
        print(f"    * Validated tasks: {before_validation} → {len(tasks)} (removed {before_validation - len(tasks)})")
        
        # Deduplicate
        tasks = Deduplicator.deduplicate(tasks)
        print(f"    * After deduplication: {len(tasks)} unique tasks")
        
        # ── SUMMARY ──────────────────────────────────────────────────────
        print("\n" + "="*60)
        print(f"  SUMMARY: Extracted {len(tasks)} action items")
        print("="*60 + "\n")
        
        return tasks


def run_pipeline(transcript: str) -> List[Dict]:
    """
    Single function entry point for pipeline.
    
    Args:
        transcript (str): Raw meeting transcript
    
    Returns:
        list: Structured task objects
    """
    extractor = NLPActionExtractor()
    return extractor.run_pipeline(transcript)
