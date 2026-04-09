"""Decision detection evaluation metrics."""

from typing import List, Dict, Tuple
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix


class DecisionDetectionMetrics:
    """
    Calculate precision, recall, F1-score for decision detection.
    
    Evaluates against gold-standard decision annotations (AMI/ICSI format).
    """
    
    @staticmethod
    def exact_match(predicted_text: str, gold_text: str) -> bool:
        """
        Check exact match (case-insensitive).
        
        Args:
            predicted_text, gold_text: Sentence texts
        
        Returns:
            bool: True if exact match
        """
        return predicted_text.strip().lower() == gold_text.strip().lower()
    
    @staticmethod
    def fuzzy_match(predicted_text: str, gold_text: str, threshold: float = 0.8) -> bool:
        """
        Check fuzzy match using string similarity.
        
        Args:
            predicted_text, gold_text: Sentence texts
            threshold: Similarity threshold (0-1)
        
        Returns:
            bool: True if similar enough
        """
        try:
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, predicted_text.lower(), gold_text.lower()).ratio()
            return ratio >= threshold
        except Exception:
            return DecisionDetectionMetrics.exact_match(predicted_text, gold_text)
    
    @staticmethod
    def semantic_match(predicted_text: str, gold_text: str, threshold: float = 0.85) -> bool:
        """
        Check semantic match using embeddings.
        
        Args:
            predicted_text, gold_text: Sentence texts
            threshold: Similarity threshold (0-1)
        
        Returns:
            bool: True if semantically similar
        """
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            
            embedder = SentenceTransformer("all-mpnet-base-v2")
            embeddings = embedder.encode([predicted_text, gold_text])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity) >= threshold
        except Exception:
            return DecisionDetectionMetrics.exact_match(predicted_text, gold_text)
    
    @staticmethod
    def compute_metrics(
        predicted_decisions: List[Dict],
        gold_decisions: List[Dict],
        match_type: str = "exact",
    ) -> Dict[str, float]:
        """
        Compute precision, recall, F1 at sentence level.
        
        Args:
            predicted_decisions: List of predicted decision dicts {"text": ...}
            gold_decisions: List of gold decision dicts {"text": ...}
            match_type: "exact", "fuzzy", or "semantic"
        
        Returns:
            Dict with precision, recall, F1, confusion matrix
            {
                "precision": 0.85,
                "recall": 0.78,
                "f1": 0.81,
                "tp": 15,
                "fp": 3,
                "fn": 4,
                "tn": 50
            }
        """
        if not gold_decisions:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": len(predicted_decisions), "fn": 0, "tn": 0}
        
        # Select match function
        if match_type == "fuzzy":
            match_fn = DecisionDetectionMetrics.fuzzy_match
        elif match_type == "semantic":
            match_fn = DecisionDetectionMetrics.semantic_match
        else:
            match_fn = DecisionDetectionMetrics.exact_match
        
        # Build gold set of matched sentences
        gold_matched = set()
        pred_matched = set()
        
        # For each predicted decision, find best match in gold
        for pred_idx, pred_decision in enumerate(predicted_decisions):
            pred_text = pred_decision.get("text", "").strip()
            if not pred_text:
                continue
            
            for gold_idx, gold_decision in enumerate(gold_decisions):
                if gold_idx in gold_matched:
                    continue
                
                gold_text = gold_decision.get("text", "").strip()
                if not gold_text:
                    continue
                
                if match_fn(pred_text, gold_text):
                    gold_matched.add(gold_idx)
                    pred_matched.add(pred_idx)
                    break
        
        # Calculate metrics
        tp = len(pred_matched)  # True positives (correctly detected)
        fp = len(predicted_decisions) - tp  # False positives (incorrectly detected)
        fn = len(gold_decisions) - len(gold_matched)  # False negatives (missed decisions)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "match_type": match_type,
        }
    
    @staticmethod
    def per_sentence_evaluation(
        predicted_decisions: List[Dict],
        gold_decisions: List[Dict],
    ) -> Dict[str, any]:
        """
        Evaluate decision detection on per-sentence basis.
        
        Assumes sentences can be aligned by position.
        
        Args:
            predicted_decisions: List dicts with 'is_decision', 'confidence'
            gold_decisions: List dicts with 'is_decision' or boolean indicators
        
        Returns:
            Dict with per-sentence metrics and lists
        """
        if len(predicted_decisions) != len(gold_decisions):
            return {"error": "Predicted and gold lists must have same length"}
        
        # Extract binary labels
        y_pred = [d.get("is_decision", False) for d in predicted_decisions]
        y_gold = [d.get("is_decision", d) for d in gold_decisions]
        
        # Compute metrics
        precision = precision_score(y_gold, y_pred, zero_division=0)
        recall = recall_score(y_gold, y_pred, zero_division=0)
        f1 = f1_score(y_gold, y_pred, zero_division=0)
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_gold, y_pred).ravel()
        
        # Per-sentence analysis
        correct = sum(1 for p, g in zip(y_pred, y_gold) if p == g)
        incorrect = sum(1 for p, g in zip(y_pred, y_gold) if p != g)
        
        # Confidence distribution
        confidences = [d.get("confidence", 0.5) for d in predicted_decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": correct / len(y_pred),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
            "correct": correct,
            "incorrect": incorrect,
            "avg_confidence": avg_confidence,
        }
    
    @staticmethod
    def confidence_analysis(predictions: List[Dict]) -> Dict[str, float]:
        """
        Analyze confidence score distribution.
        
        Args:
            predictions: List of detection results with 'confidence' field
        
        Returns:
            Dict with confidence statistics
        """
        confidences = [p.get("confidence", 0.5) for p in predictions]
        
        if not confidences:
            return {"count": 0}
        
        decisions = [p for p in predictions if p.get("is_decision", False)]
        non_decisions = [p for p in predictions if not p.get("is_decision", False)]
        
        decision_confs = [p.get("confidence", 0.5) for p in decisions]
        non_decision_confs = [p.get("confidence", 0.5) for p in non_decisions]
        
        return {
            "total": len(confidences),
            "decisions": len(decisions),
            "non_decisions": len(non_decisions),
            "avg_confidence": sum(confidences) / len(confidences),
            "avg_decision_confidence": sum(decision_confs) / len(decision_confs) if decision_confs else 0,
            "avg_non_decision_confidence": sum(non_decision_confs) / len(non_decision_confs) if non_decision_confs else 0,
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "high_confidence_decisions": sum(1 for p in decisions if p.get("confidence", 0) > 0.8),
            "low_confidence_decisions": sum(1 for p in decisions if p.get("confidence", 0) < 0.5),
        }
    
    @staticmethod
    def generate_report(
        results: Dict,
        output_file: str = None,
    ) -> str:
        """
        Generate formatted evaluation report.
        
        Args:
            results: Dict with evaluation metrics
            output_file: Optional file to write report to
        
        Returns:
            str: Formatted report text
        """
        report = []
        report.append("=" * 70)
        report.append("DECISION DETECTION EVALUATION REPORT")
        report.append("=" * 70)
        
        if "match_type" in results:
            report.append(f"\nMatch Type: {results['match_type']}")
        
        report.append(f"\nPrecision: {results.get('precision', 0):.3f}")
        report.append(f"Recall:    {results.get('recall', 0):.3f}")
        report.append(f"F1-Score:  {results.get('f1', 0):.3f}")
        
        if "accuracy" in results:
            report.append(f"Accuracy:  {results.get('accuracy', 0):.3f}")
        
        # Confusion matrix
        report.append(f"\nConfusion Matrix:")
        report.append(f"  TP (True Positives):   {results.get('tp', 0):3d}")
        report.append(f"  FP (False Positives):  {results.get('fp', 0):3d}")
        report.append(f"  FN (False Negatives):  {results.get('fn', 0):3d}")
        if "tn" in results:
            report.append(f"  TN (True Negatives):   {results.get('tn', 0):3d}")
        
        # Confidence stats
        if "avg_confidence" in results:
            report.append(f"\nAverage Confidence: {results.get('avg_confidence', 0):.3f}")
        if "avg_decision_confidence" in results:
            report.append(f"  Decisions:     {results.get('avg_decision_confidence', 0):.3f}")
            report.append(f"  Non-decisions: {results.get('avg_non_decision_confidence', 0):.3f}")
        
        report.append("\n" + "=" * 70)
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)
        
        return report_text
