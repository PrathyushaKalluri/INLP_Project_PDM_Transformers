"""Enhanced decision detection with linguistic features."""

import re
from typing import List, Dict, Optional


# Hard filter patterns: sentences that should NEVER be tasks
# These have highest priority - match before any other detection
HARD_FILTER_PATTERNS = [
    # Generic confirmations and responses
    r"^(good|great|agreed?|sounds\s+good|ok|okay|sure|hmm|yeah|yes|no)\.*$",
    # Reactions and feedback
    r"^(that'?s\s+(great|good|interesting|concerning|valid|a\s+valid\s+point))\.*$",
    # Closing/meta statements
    r"^anything\s+else",
    r"^(i\s+think\s+that\s+covers|have\s+a\s+good)",
    # Metric statements (not actionable)
    r"\d+\s*%.*compared\s+to",
    # Team reaction statements
    r"(board|team|everyone)\s+will\s+be\s+(happy|pleased|fine)",
    # Past tense observations
    r"(helped\s+drive|really\s+helped)",
    # Switching/migration without action 
    r"switched\s+to\s+a\s+competitor",
]


# Deontic modals that indicate commitment/obligation
DEONTIC_MODALS = {
    "should", "must", "need to", "have to", "ought to", "shall",
    "will", "would", "can", "could", "may", "might",  # capability/permission
    "required to", "supposed to", "expected to",  # obligation
}

# Modal strength mapping for probability boost
MODAL_STRENGTH = {
    "must": 1.0,      # strongest obligation
    "need to": 0.95,
    "have to": 0.95,
    "should": 0.85,   # weaker obligation
    "shall": 0.85,
    "let's": 0.85,    # We commit to do this together (ADD THIS)
    "will": 0.80,     # commitment
    "would": 0.70,    # weaker commitment
    "can": 0.50,      # capability only
    "could": 0.40,
    "may": 0.40,
    "might": 0.30,
    "expected to": 0.85,
    "supposed to": 0.75,
    "required to": 0.90,
    "ought to": 0.80,
}

# Sentence type-based priors for status vs task meetings
# Lower values = more skeptical (downward pressure on confidence)
SENTENCE_TYPE_PRIORS = {
    "observation": 0.2,    # Status meeting observation - heavy suppression
    "consequence": 0.25,   # Reaction/outcome - heavy suppression  
    "metric": 0.15,        # Pure metrics - almost never an action
    "general": 0.7,        # Normal statement - default
}


# Meeting type detection signals
TASK_MEETING_SIGNALS = {
    "will", "shall", "need to", "going to", "i'll", "let's",
    "by friday", "by tomorrow", "deadline", "assign", "handle",
    "responsible", "action item", "follow up", "must", "should",
}

STATUS_MEETING_SIGNALS = {
    "numbers", "revenue", "growth", "churn", "metrics", "quarter",
    "percent", "compared to", "went from", "is up", "is down",
    "looking good", "seems", "appears", "update on", "status update",
    "performance", "results", "week", "month", "year over year",
}

# Tense detection for distinguishing commitments from status updates
PAST_TENSE_INDICATORS = {
    "finished", "completed", "found", "lost", "switched", 
    "helped", "went", "heard", "complained", "mentioned",
}

PRESENT_PROGRESSIVE_VERBS = {"working", "testing", "monitoring", "running"}


def detect_meeting_type(sentences: List[Dict]) -> str:
    """
    Detect meeting type based on sentence content.
    
    Returns one of: "task_oriented", "status_review", "mixed"
    
    Args:
        sentences (List[Dict]): Sentences with 'text' key
    
    Returns:
        str: Meeting type classification
    
    Examples:
        Meeting with "I'll deploy", "finish by Friday" → "task_oriented"
        Meeting with "Revenue up 5%", "Q3 metrics" → "status_review"
        Mixed meeting → "mixed"
    """
    text = " ".join(s.get("text", "").lower() for s in sentences if s.get("text"))
    
    task_score = sum(1 for sig in TASK_MEETING_SIGNALS if sig in text)
    status_score = sum(1 for sig in STATUS_MEETING_SIGNALS if sig in text)
    
    if status_score > task_score * 1.5:
        return "status_review"
    elif task_score > status_score:
        return "task_oriented"
    else:
        return "mixed"


class DependencyFeatureAnalyzer:
    """
    Extract linguistic features from dependency parse.
    
    Uses root verb modality and object presence to adjust confidence.
    """
    
    @staticmethod
    def hard_filter(sentence_data: Dict) -> bool:
        """
        Hard filter: check if sentence matches known non-task patterns.
        
        These are sentences that should NEVER generate tasks regardless
        of transformer confidence. Run this BEFORE the transformer.
        
        Args:
            sentence_data: Dict with 'text' key
        
        Returns:
            bool: True if sentence should be hard-filtered (rejected)
        
        Examples:
            "Good" → True (confirm/reaction)
            "That's great" → True (reaction)
            "Anything else" → True (meta)
            "Revenue is up 5% compared to last quarter" → True (metric)
            "I will deploy the API" → False (not filtered)
        """
        text = sentence_data.get("text", "").lower().strip()
        
        for pattern in HARD_FILTER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def has_modal(sentence_text: str) -> Optional[str]:
        """
        Check if sentence contains deontic modal.
        
        Returns:
            Tuple (found_modal, strength) or None
        
        Examples:
            "I will deploy the API" → ("will", 0.80)
            "We should finalize pricing" → ("should", 0.85)
            "I think we should" → ("should", 0.85)
        """
        text_lower = sentence_text.lower()
        
        # Sort by length descending to match longer phrases first
        sorted_modals = sorted(DEONTIC_MODALS, key=len, reverse=True)
        
        for modal in sorted_modals:
            # Match as whole word/phrase
            pattern = r'\b' + re.escape(modal) + r'\b'
            if re.search(pattern, text_lower):
                return modal, MODAL_STRENGTH.get(modal, 0.5)
        
        return None
    
    @staticmethod
    def has_direct_object(spacy_doc) -> bool:
        """
        Check if root verb has direct object.
        
        Looks for dobj/obj dependency from root verb.
        
        Returns:
            bool: True if root verb has a direct object
        
        Examples:
            "Deploy the API" → root=Deploy, has dobj=API → True
            "I agree" → root=agree, no dobj → False
        """
        if spacy_doc is None or not hasattr(spacy_doc, 'root'):
            return False
        
        root = spacy_doc.root
        
        # Check immediate children of root verb
        for child in root.children:
            if child.dep_ in ("dobj", "obj"):
                return True
        
        return False
    
    @staticmethod
    def compute_modal_boost(sentence_data: Dict) -> float:
        """
        Compute confidence boost from modal verb.
        
        Factors:
        - Modal strength (0-1)
        - Presence of direct object (+0.1 if present)
        
        Returns:
            float: Boost factor (0-1)
        
        Examples:
            "I will deploy API" → 0.80 (will) + 0.10 (has obj) = 0.90
            "I should agree" → 0.85 (should) + 0.0 (no obj) = 0.85
            "I think yes" → 0.0 (no modal) = 0.0
        """
        text = sentence_data.get("text", "")
        modal_info = DependencyFeatureAnalyzer.has_modal(text)
        
        if modal_info is None:
            return 0.0  # No modal = no boost
        
        modal, strength = modal_info
        boost = strength
        
        # Add bonus for having a direct object (more complete commitment)
        spacy_doc = sentence_data.get("spacy_doc")
        if DependencyFeatureAnalyzer.has_direct_object(spacy_doc):
            boost += 0.10
        
        return min(boost, 1.0)  # Cap at 1.0
    
    @staticmethod
    def compute_downward_prior(sentence_data: Dict, meeting_type: str = "mixed") -> float:
        """
        Compute downward prior when no modal or object detected.
        
        This penalizes sentences that lack commitment signals.
        Also applies sentence-type-based priors (for status vs task meetings).
        
        Args:
            sentence_data: Dict with 'text' and optional 'sentence_type' keys
            meeting_type: One of "task_oriented", "status_review", "mixed"
        
        Returns:
            float: Prior penalty (0-1, multiply by baseline confidence)
        
        Examples:
            "Let's think about it" (no modal, suggestion) → 0.5
            "I agree" (no object, vague commitment) → 0.7
            Observation in status meeting → 0.2 * 0.7 = 0.14 (further suppressed)
        """
        text = sentence_data.get("text", "").lower()
        
        # Start with sentence-type-based prior if available
        sentence_type = sentence_data.get("sentence_type", "general")
        base_prior = SENTENCE_TYPE_PRIORS.get(sentence_type, 0.7)
        
        # Further suppress in status meetings
        if meeting_type == "status_review":
            base_prior *= 0.7
        
        # Check for suggestion/opinion markers (usually override type-based prior)
        suggestion_patterns = [
            r"\b(maybe|perhaps|could\s+we|might\s+we|what\s+if|think|suggest|consider)\b",
            r"\b(in\s+my\s+opinion|i\s+think|i\s+believe|it\s+seems)\b",
        ]
        
        for pattern in suggestion_patterns:
            if re.search(pattern, text):
                return 0.5  # Heavy downward prior (opinion/suggestion)
        
        # If no explicit signals override, use sentence-type-based prior
        return base_prior
    
    @staticmethod
    def detect_negation(sentence_text: str) -> bool:
        """
        Detect negation in sentence (handles false positives).
        
        Checks for explicit negation markers that indicate the sentence
        describes what will NOT happen, not what WILL happen.
        
        Returns:
            bool: True if negation detected
        
        Examples:
            "We won't fix this bug" → True (negation: won't)
            "Don't deploy to production" → True (negation: do not)
            "No further updates needed" → True (negation: no)
            "We will fix this bug" → False (no negation)
        """
        text_lower = sentence_text.lower()
        
        # Common negation markers
        negation_patterns = [
            r"\b(not|no|don't|doesn't|didn't|won't|wouldn't|can't|cannot|shouldn't|couldn't|shan't)\b",
            r"\b(never|nowhere|nothing|nobody|no\s+one)\b",
            r"\b(aren't|isn't|wasn't|weren't|haven't|hasn't|hadn't)\b",
        ]
        
        for pattern in negation_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @staticmethod
    def get_tense_prior(sentence_text: str, spacy_doc=None) -> float:
        """
        Compute downward prior based on sentence tense.
        
        Past/present-progressive tense indicates completed or ongoing work,
        not new commitments. This significantly reduces confidence.
        
        Args:
            sentence_text: Raw sentence text
            spacy_doc: Optional spaCy parsed document
        
        Returns:
            float: Tense prior (0-1, multiply with confidence)
        
        Examples:
            "I finished the search feature" → 0.2 (past: completed work)
            "I'm working on the API" → 0.3 (present progressive: ongoing)
            "I will deploy by Friday" → 1.0 (future: commitment)
            "I agree with this" → 0.7 (present: no special tense signal)
        """
        text_lower = sentence_text.lower()
        
        # Check for past tense indicators
        for past_verb in PAST_TENSE_INDICATORS:
            if past_verb in text_lower:
                return 0.2  # Heavy suppression for past tense
        
        # Check for present progressive ("working", "testing", etc.)
        for prog_verb in PRESENT_PROGRESSIVE_VERBS:
            if re.search(rf"\b{prog_verb}\b", text_lower):
                return 0.3  # Suppress present progressive (ongoing status)
        
        # Check POS tags if spaCy doc available
        if spacy_doc is not None:
            try:
                root_token = None
                for token in spacy_doc:
                    if token.dep_ == "ROOT":
                        root_token = token
                        break
                
                if root_token:
                    # Past tense: VBD (past), VBN (past participle)
                    if root_token.tag_ in {"VBD", "VBN"}:
                        return 0.2
                    
                    # Present progressive: VBG (gerund/present participle)
                    if root_token.tag_ == "VBG":
                        return 0.3
            except Exception:
                pass  # Fall through to return default
        
        return 1.0  # No special tense signal: apply normal scoring
    
    @staticmethod
    def is_request_or_question(sentence_text: str) -> bool:
        """
        Detect if sentence is a request or question.
        
        Returns:
            bool: True if sentence appears to be request/question
        
        Examples:
            "Can you deploy the API?" → True
            "Could someone handle testing?" → True
            "I will deploy the API" → False
        """
        text_lower = sentence_text.lower()
        
        # Question mark
        if "?" in sentence_text:
            return True
        
        # Request markers
        request_patterns = [
            r"\b(can\s+you|could\s+you|would\s+you|will\s+you|can\s+someone|could\s+someone)\b",
            r"\b(please|would\s+it\s+be\s+possible|is\s+it\s+possible|need\s+help)\b",
            r"\b(i\s+need|we\s+need|we\s+should|let's)\b",
        ]
        
        for pattern in request_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @staticmethod
    def is_acceptance_response(sentence_text: str) -> bool:
        """
        Detect if sentence is an acceptance/commitment response.
        
        Returns:
            bool: True if sentence appears to accept a request
        
        Examples:
            "Yes, I'll handle it" → True
            "Sure, I can do that" → True
            "Okay, will do" → True
            "I don't think so" → False
        """
        text_lower = sentence_text.lower()
        
        # Acceptance markers
        acceptance_patterns = [
            r"\b(yes|sure|okay|ok|yeah|yep|sounds\s+good|will\s+do|can\s+do)\b",
            r"\b(i'll|i\s+will|i\s+can|i\s+can\s+handle|i\s+can\s+take)\b",
            r"\b(absolutely|definitely|of\s+course|no\s+problem)\b",
        ]
        
        for pattern in acceptance_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False


class EnhancedTransformerClassifier:
    """
    Enhanced transformer classifier with context window and feature fusion.
    
    Combines base classifier with dependency tree features and context.
    """
    
    def __init__(
        self,
        base_classifier,
        include_context: bool = True,
        context_window: int = 2,
    ):
        """
        Initialize enhanced classifier.
        
        Args:
            base_classifier: Underlying transformer classifier
            include_context (bool): Whether to use prior sentences
            context_window (int): Number of prior sentences to include
        """
        self.base_classifier = base_classifier
        self.include_context = include_context
        self.context_window = context_window
        self.feature_analyzer = DependencyFeatureAnalyzer()
    
    def _build_context_text(
        self,
        sentences: List[Dict],
        current_idx: int,
    ) -> str:
        """
        Build context-enriched text for classification.
        
        Concatenates prior sentences separated by [SEP].
        
        Example:
            sentences[0]: "Alice: Let's start sprint planning"
            sentences[1]: "Bob: I'll handle the API"
            
            For sentences[1]: 
            "Let's start sprint planning [SEP] I'll handle the API"
        """
        context_texts = []
        
        # Include prior sentences within context window
        start_idx = max(0, current_idx - self.context_window)
        for i in range(start_idx, current_idx):
            context_texts.append(sentences[i]["text"])
        
        # Add current sentence
        context_texts.append(sentences[current_idx]["text"])
        
        # Join with [SEP] token
        return " [SEP] ".join(context_texts)
    
    def predict_sentence_enhanced(
        self,
        sentence: str,
        sentence_data: Optional[Dict] = None,
        sentences: Optional[List[Dict]] = None,
        current_idx: Optional[int] = None,
        meeting_type: str = "mixed",
    ) -> Dict:
        """
        Enhanced prediction with features and context.
        
        Args:
            sentence: Text to classify
            sentence_data: Dict with spacy_doc, speaker, etc.
            sentences: Full sentence list for context
            current_idx: Index in sentence list
            meeting_type: Meeting type for context-aware priors
        
        Returns:
            Dict with prediction and adjusted confidence
        """
        # Get base classifier result
        base_result = self.base_classifier.predict_sentence(sentence)
        
        # Initialize adjusted result
        adjusted_result = base_result.copy()
        adjusted_result["base_confidence"] = base_result["confidence_score"]
        
        # Skip feature enhancement if no data
        if sentence_data is None:
            return adjusted_result
        
        # Apply feature-based confidence adjustments
        modal_boost = self.feature_analyzer.compute_modal_boost(sentence_data)
        downward_prior = self.feature_analyzer.compute_downward_prior(sentence_data, meeting_type)
        tense_prior = self.feature_analyzer.get_tense_prior(sentence, sentence_data.get("spacy_doc"))
        
        # Check for negation (highest precision impact)
        has_negation = self.feature_analyzer.detect_negation(sentence)
        
        # Fusion: base score * priors + modal_boost
        # Apply both downward_prior and tense_prior to baseline
        fused_confidence = (
            base_result["confidence_score"] * downward_prior * tense_prior + modal_boost * 0.3
        )
        fused_confidence = min(fused_confidence, 1.0)
        
        # Apply negation penalty (reduces confidence significantly)
        if has_negation:
            fused_confidence = 0.1  # Negated decisions are not real commitments
        
        adjusted_result["confidence_score"] = fused_confidence
        adjusted_result["modal_boost"] = modal_boost
        adjusted_result["downward_prior"] = downward_prior
        adjusted_result["tense_prior"] = tense_prior
        adjusted_result["has_negation"] = has_negation
        adjusted_result["feature_fusion"] = fused_confidence
        
        # Optionally use context-enriched text
        if self.include_context and sentences is not None and current_idx is not None:
            context_text = self._build_context_text(sentences, current_idx)
            context_result = self.base_classifier.predict_sentence(context_text)
            
            adjusted_result["context_decision_type"] = context_result["decision_type"]
            adjusted_result["context_confidence"] = context_result["confidence_score"]
            
            # Weighted average: context (0.4) + features (0.6)
            final_confidence = (
                context_result["confidence_score"] * 0.4 +
                fused_confidence * 0.6
            )
            
            # Still apply negation penalty to final confidence
            if has_negation:
                final_confidence = 0.1
            
            adjusted_result["confidence_score"] = min(final_confidence, 1.0)
            adjusted_result["final_confidence"] = final_confidence
        
        return adjusted_result
    
    def predict_batch_enhanced(
        self,
        sentences: List[Dict],
        use_features: bool = True,
        use_context: bool = True,
        meeting_type: str = "mixed",
    ) -> List[Dict]:
        """
        Enhanced batch prediction with optional features/context.
        
        Args:
            sentences: List of sentence dicts {"text": ..., "spacy_doc": ..., ...}
            use_features: Apply dependency tree features
            use_context: Apply context window enrichment
            meeting_type: Meeting type for context-aware filtering
        
        Returns:
            List of prediction dicts with adjusted confidence
        """
        results = []
        
        for i, sent_data in enumerate(sentences):
            text = sent_data.get("text", "")
            
            result = self.predict_sentence_enhanced(
                text,
                sentence_data=sent_data if use_features else None,
                sentences=sentences if use_context else None,
                current_idx=i if use_context else None,
                meeting_type=meeting_type,
            )
            
            results.append(result)
        
        return results
