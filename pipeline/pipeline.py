"""Main NLP action extraction pipeline."""

from typing import List, Dict

from .config import (
    USE_TRANSFORMER_CLASSIFIER,
    USE_RULE_BASED_DETECTION,
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
        # ── STEP 1: PREPROCESSING ────────────────────────────────────────
        speaker_utterances = parse_speakers(transcript)
        
        # Extract unique speakers for assignee extraction
        self.known_speakers = set(s.get("speaker", "") for s in speaker_utterances if s.get("speaker"))
        self.assignee_extractor.set_known_speakers(self.known_speakers)
        
        sentences = split_sentences(speaker_utterances)
        sentences = clean_sentences(sentences)
        sentences = filter_stopwords(sentences)
        sentences = resolve_triplets(sentences)
        
        # Flag sentence types (observation, consequence, metric, general)
        sentences = flag_sentence_types(sentences)
        
        # Detect meeting type (task_oriented, status_review, mixed)
        from .detection.enhanced_features import detect_meeting_type
        meeting_type = detect_meeting_type(sentences)
        self.meeting_type = meeting_type
        
        # ── STEP 2: DETECTION ────────────────────────────────────────────
        detected = self.detector.detect_batch(sentences, meeting_type=self.meeting_type)
        decision_sentences = [s for s in detected if s.get("is_decision")]
        
        if not decision_sentences:
            return []
        
        # ── STEP 3: EXTRACTION ───────────────────────────────────────────
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
        
        # ── STEP 4: POSTPROCESSING ───────────────────────────────────────
        # Build tasks (includes description generation)
        tasks = TaskBuilder.build_batch(task_definitions)
        
        # Score confidence
        tasks = ConfidenceScorer.score_batch(tasks)
        
        # Add manual review flags for borderline confidence
        tasks = TaskValidator.add_manual_review_flags(tasks)
        
        # Filter invalid tasks (metrics, reactions, etc.)
        tasks = TaskValidator.filter_batch(tasks, meeting_type=self.meeting_type)
        
        # Deduplicate
        tasks = Deduplicator.deduplicate(tasks)
        
        return tasks


def run_pipeline(transcript: str) -> dict:
    """
    Single function entry point for pipeline.
    
    FIXED CONTRACT (Phase X: Result Persistence):
    Returns a dict with guaranteed structure:
    {
      "summary": {
        "summary_text": str | None
      },
      "action_items": [
        {
          "title": str,
          "description": str,
          "assignee": str | None,
          "deadline": str | None
        }
      ]
    }
    
    Args:
        transcript (str): Raw meeting transcript
    
    Returns:
        dict: Contract-compliant dict with summary and action_items
        
    Guarantees:
        - Never returns None (always returns dict)
        - Always has "summary" and "action_items" keys
        - action_items is always a list (may be empty)
        - All action items have required fields
    """
    extractor = NLPActionExtractor()
    tasks = extractor.run_pipeline(transcript)
    
    # Map tasks to action_items contract
    action_items = []
    for task in tasks:
        action_items.append({
            "title": task.get("task", ""),
            "description": task.get("task", ""),
            "assignee": task.get("assignee"),
            "deadline": task.get("deadline"),
        })
    
    # Return in contract format
    return {
        "summary": {
            "summary_text": None  # Will be populated from meeting summary later
        },
        "action_items": action_items
    }
