"""Domain-specific stopword filter to remove non-actionable sentences."""

import re
from typing import List, Dict


# Pattern-based filler/non-task detection (replaces simple string matching)
# Catches greetings, fillers, acknowledgements, and meta-conversation
FILLER_PATTERNS = [
    # Greetings / closings
    r"^(good\s+(morning|afternoon|evening|night)|hello|hi\s+everyone)\b",
    r"^(thanks?|thank\s+you)(\s+everyone|\s+all|\s+guys?)?\s*[.!]?$",
    r"^(have\s+a\s+(good|great|nice)).*week",
    r"^(sounds?\s+good|great[.!]?|perfect[.!]?|awesome[.!]?)$",
    
    # Single-word or near-empty (these are never actionable)
    r"^\w+[.!?]?$",                          # single word sentences
    r"^(yes|no|ok|okay|sure|agreed?)[,.]?$", # single acknowledgements
    r"^(yeah|yep|nope|hmm|right)[.!]?$",
    
    # Transition phrases / meta-conversation
    r"^(one\s+(last|more)\s+thing)\b",
    r"^(anyway|alright|so+|well+)[,.]",
    r"^(quick\s+standup|let'?s\s+go\s+around)\b",
    r"^let\s+me\s+know\b",
    r"^appreciate\s+it\b",
    r"^makes\s+sense\b",
    
    # Pure questions with no action intent
    r"^(anything\s+else|any\s+(other|questions|concerns))\b",
    r"^what'?s\s+your\s+(status|update|progress)\b",
    
    # Reactions and assessments (not tasks)
    r"^(good\s+idea|i\s+like\s+that|i\s+agree)\b",
    r"^(that'?s\s+great|that'?s\s+good|that'?s\s+interesting)\b",
    
    # Empty or purely punctuation
    r"^\s*[.!?,;:\-]+\s*$",
    
    # Colloquialisms and fillers
    r"^(got\s+it|will\s+do|no\s+problem|absolutely|definitely|exactly)\b",
    r"^(fine[.!]?|sure\s+thing)\b",
]


def is_stop_sentence(text: str) -> bool:
    """
    Check if a sentence should be filtered out using pattern matching.
    
    Identifies filler sentences, greetings, acknowledgements, and other
    non-actionable utterances that waste detection capacity.
    
    Args:
        text (str): Sentence to check
    
    Returns:
        bool: True if sentence is a filler (should be filtered)
    
    Examples:
        "Great work." → True
        "One last thing." → True
        "Quick standup." → True
        "Thanks everyone." → True
        "Yes." → True
        "I will fix the bug." → False
    """
    normalized = text.strip()
    
    # Check against all filler patterns
    for pattern in FILLER_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return True
    
    return False


def filter_stopwords(sentences: List[Dict]) -> List[Dict]:
    """
    Remove stop sentences from list.
    
    Args:
        sentences (List[Dict]): List of sentence dictionaries
    
    Returns:
        List[Dict]: Filtered sentences
    """
    filtered = []
    removed_count = 0
    
    for sent in sentences:
        text = sent.get("text", "")
        
        if is_stop_sentence(text):
            removed_count += 1
            continue
        
        filtered.append(sent)
    
    if removed_count > 0:
        print(f"[*] Stopword filter: removed {removed_count} non-actionable sentences")
    
    return filtered
