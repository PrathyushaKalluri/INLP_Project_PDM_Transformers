"""Metrics calculation for task extraction evaluation."""

from typing import List, Dict, Tuple
from collections import defaultdict


class MetricsCalculator:
    """
    Calculate evaluation metrics for task extraction.
    
    Supports precision, recall, F1-score and other quality metrics
    for comparing predicted tasks against gold-standard annotations.
    """
    
    @staticmethod
    def exact_match(predicted: str, gold: str) -> bool:
        """
        Check exact string match (case-insensitive).
        
        Args:
            predicted, gold: Task descriptions
        
        Returns:
            bool: True if exact match
        """
        return predicted.strip().lower() == gold.strip().lower()
    
    @staticmethod
    def partial_match(predicted: str, gold: str, threshold: float = 0.7) -> bool:
        """
        Check partial/fuzzy match using Levenshtein distance.
        
        Args:
            predicted, gold: Task descriptions
            threshold: Similarity threshold (0-1)
        
        Returns:
            bool: True if similar enough
        """
        try:
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, predicted.lower(), gold.lower()).ratio()
            return ratio >= threshold
        except Exception:
            return MetricsCalculator.exact_match(predicted, gold)
    
    @staticmethod
    def semantic_match(predicted: str, gold: str, threshold: float = 0.8) -> bool:
        """
        Check semantic similarity using embeddings.
        
        Args:
            predicted, gold: Task descriptions
            threshold: Similarity threshold (0-1)
        
        Returns:
            bool: True if semantically similar
        """
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            
            embedder = SentenceTransformer("all-mpnet-base-v2")
            embeddings = embedder.encode([predicted, gold])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity) >= threshold
        except Exception as e:
            print(f"[!] Semantic match failed: {e}")
            return MetricsCalculator.exact_match(predicted, gold)
    
    @staticmethod
    def extract_metrics(
        predicted_tasks: List[Dict],
        gold_tasks: List[Dict],
        match_type: str = "semantic"
    ) -> Dict[str, float]:
        """
        Calculate precision, recall, F1-score.
        
        Args:
            predicted_tasks: Predicted task list (each with 'task' field)
            gold_tasks: Gold-standard task list
            match_type: "exact", "partial", or "semantic"
        
        Returns:
            Dict with precision, recall, F1-score
        """
        if not gold_tasks:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        if not predicted_tasks:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        # Match function
        if match_type == "exact":
            match_fn = MetricsCalculator.exact_match
        elif match_type == "partial":
            match_fn = MetricsCalculator.partial_match
        elif match_type == "semantic":
            match_fn = MetricsCalculator.semantic_match
        else:
            match_fn = MetricsCalculator.exact_match
        
        # Track matched gold tasks
        gold_matched = set()
        predicted_matched = set()
        
        # For each predicted task, find best matching gold task
        for pred_idx, pred_task in enumerate(predicted_tasks):
            pred_text = pred_task.get("task", "").strip()
            if not pred_text:
                continue
            
            for gold_idx, gold_task in enumerate(gold_tasks):
                if gold_idx in gold_matched:
                    continue
                
                gold_text = gold_task.get("task", "").strip()
                if not gold_text:
                    continue
                
                if match_fn(pred_text, gold_text):
                    gold_matched.add(gold_idx)
                    predicted_matched.add(pred_idx)
                    break
        
        # Calculate metrics
        tp = len(predicted_matched)  # True positives
        fp = len(predicted_tasks) - tp  # False positives
        fn = len(gold_tasks) - len(gold_matched)  # False negatives
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn
        }
    
    @staticmethod
    def extraction_quality(tasks: List[Dict]) -> Dict[str, float]:
        """
        Assess quality of extraction (confidence, completeness).
        
        Args:
            tasks: List of task objects with confidence and metadata
        
        Returns:
            Dict with quality metrics
        """
        if not tasks:
            return {
                "avg_confidence": 0.0,
                "completeness": 0.0,
                "na_rate": 0.0
            }
        
        total_confidence = sum(t.get("confidence", 0) for t in tasks)
        avg_confidence = total_confidence / len(tasks)
        
        # Completeness: proportion of tasks with all required fields
        required_fields = {"task", "assignee", "deadline"}
        complete_count = sum(
            1 for t in tasks
            if all(t.get(field) for field in required_fields)
        )
        completeness = complete_count / len(tasks)
        
        # N/A rate: proportion with missing required fields
        na_count = sum(
            1 for t in tasks
            if not all(t.get(field) for field in required_fields)
        )
        na_rate = na_count / len(tasks)
        
        return {
            "avg_confidence": avg_confidence,
            "completeness": completeness,
            "na_rate": na_rate,
            "total_tasks": len(tasks)
        }
    
    @staticmethod
    def detection_quality(decisions: List[Dict]) -> Dict[str, float]:
        """
        Assess quality of decision detection.
        
        Args:
            decisions: List of detected decisions
        
        Returns:
            Dict with detection quality metrics
        """
        if not decisions:
            return {
                "total": 0,
                "avg_confidence": 0.0,
                "high_confidence": 0.0
            }
        
        total = len(decisions)
        confidences = [d.get("confidence", 0) for d in decisions]
        avg_confidence = sum(confidences) / total if total > 0 else 0.0
        
        high_conf = sum(1 for c in confidences if c > 0.8)
        high_confidence_ratio = high_conf / total if total > 0 else 0.0
        
        return {
            "total": total,
            "avg_confidence": avg_confidence,
            "high_confidence": high_confidence_ratio
        }
