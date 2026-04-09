"""Preprocessing module for transcript processing."""

from typing import List, Dict
from .speaker_parser import parse_speakers
from .sentence_splitter import split_sentences
from .cleaner import clean_text, clean_sentences, normalize_indian_english, flag_sentence_types
from .stopword_filter import filter_stopwords, is_stop_sentence
from .triplet_resolver import resolve_triplets


def normalize_to_meeting_format(sentences: List[Dict], keep_metadata: bool = True) -> List[Dict]:
    """
    Normalize preprocessed sentences to meeting.json format.
    
    Args:
        sentences (List[Dict]): Preprocessed sentence dicts with extra fields
        keep_metadata (bool): If True, keep linguistic features (root_verb, object, subject, turn_id, timestamp)
                             If False, keep only {sentence_id, speaker, text}
    
    Returns:
        List[Dict]: Normalized dicts
    """
    if not keep_metadata:
        # Minimal format: just sentence_id, speaker, text
        return [
            {
                "sentence_id": sent["sentence_id"],
                "speaker": sent["speaker"],
                "text": sent["text"],
            }
            for sent in sentences
        ]
    
    # Keep all metadata from preprocessing
    normalized = []
    for sent in sentences:
        normalized_sent = {
            "sentence_id": sent["sentence_id"],
            "speaker": sent["speaker"],
            "text": sent["text"],
            "root_verb": sent.get("root_verb"),
            "object": sent.get("object"),
            "subject": sent.get("subject"),
        }
        # Add optional fields if present
        if "turn_id" in sent:
            normalized_sent["turn_id"] = sent["turn_id"]
        if "timestamp" in sent:
            normalized_sent["timestamp"] = sent["timestamp"]
        
        # Add post-processing fields if present
        if "object_resolved" in sent:
            normalized_sent["object_resolved"] = sent["object_resolved"]
        if "subject_resolved" in sent:
            normalized_sent["subject_resolved"] = sent["subject_resolved"]
        if "triplet_confidence" in sent:
            normalized_sent["triplet_confidence"] = sent["triplet_confidence"]
        if "triplet_flags" in sent:
            normalized_sent["triplet_flags"] = sent["triplet_flags"]
        
        normalized.append(normalized_sent)
    
    return normalized


__all__ = [
    "parse_speakers",
    "split_sentences",
    "clean_text",
    "clean_sentences",
    "normalize_indian_english",
    "filter_stopwords",
    "is_stop_sentence",
    "normalize_to_meeting_format",
    "post_process_metadata",
]
