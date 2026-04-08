"""Hybrid detection combining rule-based and transformer approaches."""

from typing import List, Dict, Optional
from .rule_based import RuleBasedDetector
from .classifier import TransformerClassifier, KEEP_TYPES
from .enhanced_features import EnhancedTransformerClassifier


class HybridDetector:
    """
    Combines rule-based, transformer, and linguistic feature detection.
    
    Prioritizes precision using:
    1. Dependency tree features (modal verbs, direct objects)
    2. Context window enrichment (prior 2 sentences)
    3. Transformer-based zero-shot classification
    
    Three-zone threshold system:
    - HIGH (0.7-1.0): Auto-accept as decision
    - REVIEW (0.4-0.7): Manual review needed
    - LOW (0-0.4): Auto-reject
    """
    
    # Three-zone thresholds for manual review workflow
    THRESHOLD_HIGH = 0.7    # Auto-accept boundary
    THRESHOLD_REVIEW = 0.4  # Manual review boundary
    
    def __init__(
        self,
        use_transformer: bool = True,
        use_features: bool = True,
        use_context: bool = True,
        context_window: int = 2,
    ):
        """
        Initialize hybrid detector with optional enhancements.
        
        Args:
            use_transformer (bool): Whether to use transformer classifier
            use_features (bool): Use dependency tree features
            use_context (bool): Use context window enrichment
            context_window (int): Number of prior sentences
        """
        self.rule_detector = RuleBasedDetector()
        self.base_transformer = TransformerClassifier() if use_transformer else None
        self.enhanced_transformer = None
        
        if use_transformer and use_features:
            self.enhanced_transformer = EnhancedTransformerClassifier(
                self.base_transformer,
                include_context=use_context,
                context_window=context_window,
            )
        
        self.use_transformer = use_transformer
        self.use_features = use_features
        self.use_context = use_context
    
    @staticmethod
    def compute_confidence_zone(confidence: float) -> str:
        """
        Map confidence score to review zone.
        
        Args:
            confidence (float): Confidence score (0-1)
        
        Returns:
            str: "high", "review", or "low"
        """
        if confidence >= HybridDetector.THRESHOLD_HIGH:
            return "high"
        elif confidence >= HybridDetector.THRESHOLD_REVIEW:
            return "review"
        else:
            return "low"
    
    @staticmethod
    def detect_turn_pair_acceptances(results: List[Dict]) -> List[Dict]:
        """
        Detect turn-pair request-acceptance patterns.
        
        If sentence N is a request/question and sentence N+1 is acceptance,
        mark N+1 as a decision with turn_pair_acceptance marker.
        
        This captures implicit commitments from acceptance responses.
        
        Args:
            results (List[Dict]): Detected sentences with decision info
        
        Returns:
            List[Dict]: Updated results with turn_pair detection
        """
        from .enhanced_features import DependencyFeatureAnalyzer
        
        for i in range(len(results) - 1):
            current = results[i]
            next_sent = results[i + 1]
            current_text = current.get("text", "")
            next_text = next_sent.get("text", "")
            
            # Check if current is request/question and next is acceptance
            if (
                DependencyFeatureAnalyzer.is_request_or_question(current_text) and
                DependencyFeatureAnalyzer.is_acceptance_response(next_text)
            ):
                # Mark next sentence as decision from turn-pair
                next_sent["is_turn_pair_acceptance"] = True
                next_sent["paired_request_idx"] = i
                next_sent["is_decision"] = True
                
                # Boost confidence since it's an explicit commitment
                if next_sent.get("confidence", 0) < 0.8:
                    next_sent["confidence"] = 0.85
                    next_sent["confidence_zone"] = "high"
        
        return results
    
    def detect_batch(
        self,
        sentences: List[Dict],
        use_transformer: bool = None,
        use_features: bool = None,
        use_context: bool = None,
        meeting_type: str = "mixed",
    ) -> List[Dict]:
        """
        Detect decisions using hybrid approach with optional enhancements.
        
        Args:
            sentences (List[Dict]): List of sentence dictionaries with 'text' and optionally 'spacy_doc'
            use_transformer (bool): Override default transformer usage
            use_features (bool): Override feature usage
            use_context (bool): Override context usage
            meeting_type (str): Meeting type ("task_oriented", "status_review", "mixed") for context-aware filtering
        
        Returns:
            List[Dict]: Augmented sentences with decision detection results
        """
        use_tf = use_transformer if use_transformer is not None else self.use_transformer
        use_feat = use_features if use_features is not None else self.use_features
        use_ctx = use_context if use_context is not None else self.use_context
        
        # First pass: rule-based detection (efficient filtering)
        results = self.rule_detector.detect_batch(sentences)
        
        if not use_tf or self.base_transformer is None:
            return results
        
        # HARD FILTER PASS: Check for known non-task patterns before transformer
        # This eliminates obvious false positives before expensive transformer inference
        from .enhanced_features import DependencyFeatureAnalyzer
        for i, sent in enumerate(results):
            if DependencyFeatureAnalyzer.hard_filter(sent):
                sent["is_decision"] = False
                sent["hard_filtered"] = True
                sent["confidence"] = 0.1
                sent["confidence_zone"] = "low"
                sent["requires_manual_review"] = False
        
        # Second pass: transformer with optional enhancements
        if use_feat and self.enhanced_transformer is not None:
            transformer_results = self.enhanced_transformer.predict_batch_enhanced(
                sentences,
                use_features=use_feat,
                use_context=use_ctx,
                meeting_type=meeting_type,
            )
        else:
            transformer_results = self.base_transformer.predict_batch(
                [s["text"] for s in sentences]
            )
        
        # Merge results with confidence fusion
        final_results = []
        for i, result in enumerate(results):
            # Skip transformer scoring if hard filtered
            if result.get("hard_filtered"):
                final_results.append(result)
                continue
            
            tf_result = transformer_results[i]
            decision_type = tf_result["decision_type"]
            confidence = tf_result["confidence_score"]
            
            # Compute confidence zone
            confidence_zone = self.compute_confidence_zone(confidence)
            
            # Three-zone decision logic
            is_decision = (
                decision_type in KEEP_TYPES and
                confidence_zone in ("high", "review")  # Include high and review zones
            )
            
            merged = {
                **result,
                "transformer_decision_type": decision_type,
                "transformer_confidence": tf_result.get("base_confidence", confidence),
                "confidence": confidence,  # Final confidence score
                "confidence_zone": confidence_zone,  # NEW: high/review/low
                "is_decision": is_decision or result["is_decision"],
                "method": "hybrid",
                "requires_manual_review": confidence_zone == "review",  # NEW: review flag
            }
            
            # Include enhancement details if available
            if use_feat and "modal_boost" in tf_result:
                merged["modal_boost"] = tf_result["modal_boost"]
                merged["downward_prior"] = tf_result["downward_prior"]
                merged["has_negation"] = tf_result.get("has_negation", False)
                merged["adjusted_confidence"] = confidence
            
            if use_ctx and "context_confidence" in tf_result:
                merged["context_decision_type"] = tf_result.get("context_decision_type")
                merged["context_confidence"] = tf_result.get("context_confidence")
            
            final_results.append(merged)
        
        # Post-processing: Detect turn-pair request-acceptance patterns
        final_results = self.detect_turn_pair_acceptances(final_results)
        
        return final_results

