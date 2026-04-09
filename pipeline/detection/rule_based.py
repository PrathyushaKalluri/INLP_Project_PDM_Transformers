"""Rule-based decision detection using pattern matching."""

import re
from typing import List, Dict


# Patterns for non-actionable sentences
NON_ACTION_PATTERNS = [
    # Greetings and pleasantries
    re.compile(r"^\s*good\s+(morning|afternoon|evening|day)\b", re.I),
    re.compile(r"^\s*(hi|hello|hey|welcome)\b", re.I),
    re.compile(r"^\s*thanks?\s+(for|everyone|all)\b", re.I),
    # Short confirmations
    re.compile(
        r"^\s*(sure|perfect|great|sounds?\s+good|agreed|absolutely|no\s+problem"
        r"|will\s+do|okay|ok|fine|right|exactly|definitely)\s*\.?\s*$",
        re.I,
    ),
    # Meeting facilitation
    re.compile(
        r"^\s*let'?s\s+(start|begin|get\s+started|move\s+on|kick\s+off"
        r"|meet\s+again|schedule\s+(a\s+)?follow|wrap\s+up)\b",
        re.I,
    ),
    # Pure observations
    re.compile(r"^\s*the\s+\w+\s+(is|are|was|were)\s+(too|very|really)\b", re.I),
]

# Pattern for action verbs
ACTION_VERBS = re.compile(
    r"\b(prepare|create|write|send|deploy|build|design|test|review|approve"
    r"|schedule|organize|coordinate|finalize|update|implement|document"
    r"|setup|configure|integrate|optimize|monitor|debug|fix|investigate"
    r"|analyze|research|verify|validate|check|plan|propose|suggest"
    r"|draft|outline|summarize|compile|generate|migrate|refactor|audit)\b",
    re.I,
)

MIN_DECISION_WORDS = 4


class RuleBasedDetector:
    """
    Rule-based detector for decision-related sentences using pattern matching.
    
    Uses action verb detection and pattern-based filtering.
    """
    
    def __init__(self, min_words: int = MIN_DECISION_WORDS):
        """Initialize rule-based detector."""
        self.min_words = min_words
    
    def is_actionable(self, text: str) -> bool:
        """
        Determine if a sentence is actionable using rules.
        
        Returns True if:
        - Contains action verb
        - Meets minimum word count
        - Not matching non-actionable patterns
        """
        if not text or len(text.split()) < self.min_words:
            return False
        
        for pattern in NON_ACTION_PATTERNS:
            if pattern.search(text):
                return False
        
        return bool(ACTION_VERBS.search(text))
    
    def detect_batch(self, sentences: List[Dict]) -> List[Dict]:
        """
        Apply rule-based detection to list of sentences.
        
        Args:
            sentences (List[Dict]): Sentence dictionaries with 'text' key
        
        Returns:
            List[Dict]: Augmented sentences with 'is_decision' and 'confidence' keys
        """
        results = []
        for sent in sentences:
            is_decision = self.is_actionable(sent["text"])
            results.append({
                **sent,
                "is_decision": is_decision,
                "confidence": 1.0 if is_decision else 0.0,
                "method": "rule_based"
            })
        
        return results
