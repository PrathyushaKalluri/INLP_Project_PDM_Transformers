"""Evaluation framework for task extraction pipeline."""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .metrics import MetricsCalculator


class Evaluator:
    """
    Evaluate task extraction pipeline against gold-standard annotations.
    
    Supports evaluation at different steps:
    - Decision detection evaluation (Step 2)
    - Task extraction evaluation (Steps 3-4)
    """
    
    def __init__(self, gold_annotations_dir: str = "data/labeled"):
        """
        Initialize evaluator with gold annotations directory.
        
        Args:
            gold_annotations_dir: Path to folder containing gold annotations
        """
        self.gold_dir = Path(gold_annotations_dir)
        self.metrics = MetricsCalculator()
    
    def load_gold_tasks(self, meeting_id: str) -> List[Dict]:
        """
        Load gold-standard task annotations for a meeting.
        
        Args:
            meeting_id: Meeting identifier (e.g., "meeting1")
        
        Returns:
            List of annotated tasks
        """
        gold_file = self.gold_dir / f"{meeting_id}_tasks_gold.json"
        
        if not gold_file.exists():
            print(f"[!] Gold file not found: {gold_file}")
            return []
        
        try:
            with open(gold_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading gold annotations: {e}")
            return []
    
    def load_gold_decisions(self, meeting_id: str) -> List[Dict]:
        """
        Load gold-standard decision annotations for a meeting.
        
        Args:
            meeting_id: Meeting identifier
        
        Returns:
            List of annotated decisions
        """
        gold_file = self.gold_dir / f"{meeting_id}_decisions_gold.json"
        
        if not gold_file.exists():
            print(f"[!] Gold decisions file not found: {gold_file}")
            return []
        
        try:
            with open(gold_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading gold decisions: {e}")
            return []
    
    def evaluate_tasks(
        self,
        predicted_tasks: List[Dict],
        meeting_id: str,
        match_type: str = "semantic"
    ) -> Dict:
        """
        Evaluate predicted tasks against gold annotations.
        
        Args:
            predicted_tasks: Tasks from pipeline
            meeting_id: Meeting identifier for loading gold annotations
            match_type: "exact", "partial", or "semantic"
        
        Returns:
            Dict with evaluation results
        """
        gold_tasks = self.load_gold_tasks(meeting_id)
        
        if not gold_tasks:
            print(f"[!] No gold annotations for {meeting_id}")
            return {}
        
        # Extract metrics
        extraction_metrics = self.metrics.extract_metrics(
            predicted_tasks,
            gold_tasks,
            match_type=match_type
        )
        
        # Quality metrics
        quality_metrics = self.metrics.extraction_quality(predicted_tasks)
        
        return {
            "evaluation": "task_extraction",
            "meeting_id": meeting_id,
            "match_type": match_type,
            "extraction_metrics": extraction_metrics,
            "quality_metrics": quality_metrics,
            "gold_count": len(gold_tasks),
            "predicted_count": len(predicted_tasks)
        }
    
    def evaluate_decisions(
        self,
        predicted_decisions: List[Dict],
        meeting_id: str
    ) -> Dict:
        """
        Evaluate detected decisions against gold annotations.
        
        Args:
            predicted_decisions: Decisions from Step 2
            meeting_id: Meeting identifier
        
        Returns:
            Dict with evaluation results
        """
        gold_decisions = self.load_gold_decisions(meeting_id)
        
        if not gold_decisions:
            print(f"[!] No gold decision annotations for {meeting_id}")
            return {}
        
        # Extract metrics for decisions
        extraction_metrics = self.metrics.extract_metrics(
            predicted_decisions,
            gold_decisions,
            match_type="semantic"
        )
        
        # Detection quality
        detection_quality = self.metrics.detection_quality(predicted_decisions)
        
        return {
            "evaluation": "decision_detection",
            "meeting_id": meeting_id,
            "extraction_metrics": extraction_metrics,
            "detection_quality": detection_quality,
            "gold_count": len(gold_decisions),
            "predicted_count": len(predicted_decisions)
        }
    
    def evaluate_all_meetings(
        self,
        predictions_dir: str = "data/outputs",
        match_type: str = "semantic"
    ) -> Dict[str, Dict]:
        """
        Evaluate all meetings in predictions directory.
        
        Args:
            predictions_dir: Directory with predicted task JSON files
            match_type: "exact", "partial", or "semantic"
        
        Returns:
            Dict mapping meeting_id -> evaluation results
        """
        pred_dir = Path(predictions_dir)
        results = {}
        
        # Find all task predictions
        for task_file in pred_dir.glob("*_tasks.json"):
            meeting_id = task_file.stem.replace("_tasks", "")
            
            try:
                with open(task_file, "r") as f:
                    predicted_tasks = json.load(f)
                
                eval_result = self.evaluate_tasks(
                    predicted_tasks,
                    meeting_id,
                    match_type=match_type
                )
                results[meeting_id] = eval_result
                
            except Exception as e:
                print(f"[!] Error evaluating {meeting_id}: {e}")
        
        return results
    
    def print_evaluation_report(self, results: Dict) -> None:
        """
        Print formatted evaluation report.
        
        Args:
            results: Evaluation results from evaluate_all_meetings()
        """
        print("\n" + "="*60)
        print("TASK EXTRACTION EVALUATION REPORT")
        print("="*60)
        
        for meeting_id, eval_result in results.items():
            if not eval_result:
                print(f"\n{meeting_id}: [SKIPPED - no gold annotations]")
                continue
            
            print(f"\n{meeting_id}:")
            extract_metrics = eval_result.get("extraction_metrics", {})
            quality_metrics = eval_result.get("quality_metrics", {})
            
            print(f"  Gold: {eval_result.get('gold_count', 0)} tasks")
            print(f"  Predicted: {eval_result.get('predicted_count', 0)} tasks")
            print(f"  Precision: {extract_metrics.get('precision', 0):.3f}")
            print(f"  Recall: {extract_metrics.get('recall', 0):.3f}")
            print(f"  F1-Score: {extract_metrics.get('f1', 0):.3f}")
            print(f"  Completeness: {quality_metrics.get('completeness', 0):.3f}")
            print(f"  Avg Confidence: {quality_metrics.get('avg_confidence', 0):.3f}")
        
        print("\n" + "="*60)
