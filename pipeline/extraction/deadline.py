"""Extract deadline information from task context."""

import re
from typing import List, Dict, Optional


# Pre-compiled deadline patterns (compiled once at module load, not per call)
_DEADLINE_PATTERN_STRINGS = [
    r"\bby\s+(end\s+of\s+)?(next\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june"
    r"|july|august|september|october|november|december"
    r"|tomorrow|today|tonight|week|month|quarter"
    r"|Q[1-4])\b",
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|week|month|quarter)\b",
    r"\bend\s+of\s+(the\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june"
    r"|july|august|september|october|november|december"
    r"|week|month|quarter)\b",
    r"\b(january|february|march|april|may|june"
    r"|july|august|september|october|november|december)"
    r"\s+\d{1,2}\b",
    r"\b\d{1,2}\s+(january|february|march|april|may|june"
    r"|july|august|september|october|november|december)\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b",
    r"\btomorrow\b",
    r"\btoday\b",
]
DEADLINE_PATTERNS = [re.compile(p, re.I) for p in _DEADLINE_PATTERN_STRINGS]

_INVALID_DEADLINE_PATTERNS = [
    re.compile(r"^\s*(morning|afternoon|evening|night)\s*$", re.I),
    re.compile(r"\b(last|previous|earlier|recently|ago)\b", re.I),
    re.compile(r"^\s*the\s+task\s+week\s*$", re.I),
]

_VALID_DEADLINE_ANCHORS = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june|july|august|september"
    r"|october|november|december"
    r"|tomorrow|today|tonight|end\s+of"
    r"|next\s+week|next\s+month|next\s+quarter"
    r"|Q[1-4])\b",
    re.I,
)


class DeadlineExtractor:
    """
    Extract deadline from task context using NER-based or regex methods.
    
    Falls back to regex-based deadline extraction if spaCy NER unavailable.
    """
    
    def __init__(self):
        """Initialize deadline extractor."""
        self._nlp = None
        self.use_spacy = False
    
    def _ensure_loaded(self):
        """Lazy-load spaCy NER model."""
        if self._nlp is not None:
            return
        
        try:
            # Reuse the spaCy model already loaded by sentence_splitter
            from ..preprocessing.sentence_splitter import load_nlp_model
            self._nlp = load_nlp_model()
            self.use_spacy = True
            print(f"[+] spaCy NER model loaded")
        except Exception as e:
            print(f"[!] Warning: Could not load spaCy NER: {e}")
            print(f"[!] Falling back to regex-based deadline extraction")
    
    def _is_valid_deadline(self, text: str) -> bool:
        """Check if extracted deadline is valid."""
        if not text or len(text.strip()) < 3:
            return False
        
        for pat in _INVALID_DEADLINE_PATTERNS:
            if pat.search(text):
                return False
        
        if not _VALID_DEADLINE_ANCHORS.search(text):
            return False
        
        return True
    
    def _regex_extract(self, text: str) -> Optional[str]:
        """Extract deadline using pre-compiled regex patterns."""
        patterns = DEADLINE_PATTERNS  # Already pre-compiled at module level
        
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                deadline = match.group(0).strip()
                if self._is_valid_deadline(deadline):
                    return deadline
        
        return None
    
    def _spacy_extract(self, text: str) -> Optional[str]:
        """Extract deadline using spaCy NER."""
        self._ensure_loaded()
        
        if not self.use_spacy:
            return self._regex_extract(text)
        
        try:
            doc = self._nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("DATE", "TIME"):
                    deadline = ent.text.strip()
                    if self._is_valid_deadline(deadline):
                        return deadline
        except Exception as e:
            print(f"[!] spaCy extraction failed: {e}")
        
        return self._regex_extract(text)
    
    def extract(self, sentence_text: str) -> Optional[str]:
        """
        Extract deadline from sentence text.
        
        Args:
            sentence_text (str): Task description sentence
        
        Returns:
            str: Deadline expression or None
        """
        return self._spacy_extract(sentence_text)
