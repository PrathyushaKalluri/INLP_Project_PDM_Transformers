"""Detection module for extracting tasks from transcripts."""

from .rule_based import RuleBasedDetector
from .classifier import TransformerClassifier
from .hybrid_detector import HybridDetector
from .enhanced_features import DependencyFeatureAnalyzer, EnhancedTransformerClassifier

__all__ = [
    "RuleBasedDetector",
    "TransformerClassifier",
    "HybridDetector",
    "DependencyFeatureAnalyzer",
    "EnhancedTransformerClassifier",
]
