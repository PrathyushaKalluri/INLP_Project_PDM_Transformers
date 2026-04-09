"""Assign confidence scores to tasks."""

from typing import List, Dict


class ConfidenceScorer:
    """
    Assigns confidence scores to tasks based on extraction quality.
    """
    
    @staticmethod
    def compute_confidence(
        detection_confidence: float = 1.0,
        extraction_completeness: float = 1.0,
        assignment_confidence: float = 1.0,
        deadline_confidence: float = 1.0,
    ) -> float:
        """
        Compute overall task confidence score.
        
        Args:
            detection_confidence: How confident we are about task detection (0-1)
            extraction_completeness: How much information was successfully extracted (0-1)
            assignment_confidence: How confident about assignee (0-1)
            deadline_confidence: How confident about deadline (0-1)
        
        Returns:
            float: Overall confidence score (0-1)
        """
        # Weight average: detection has highest weight
        scores = [
            detection_confidence * 0.5,
            extraction_completeness * 0.2,
            assignment_confidence * 0.15,
            deadline_confidence * 0.15,
        ]
        return min(1.0, max(0.0, sum(scores)))
    
    @staticmethod
    def score_batch(tasks: List[Dict]) -> List[Dict]:
        """
        Add confidence scores to list of tasks.
        
        Args:
            tasks (List[Dict]): Task objects
        
        Returns:
            List[Dict]: Tasks with updated confidence scores
        """
        scored_tasks = []
        for task in tasks:
            confidence = ConfidenceScorer.compute_confidence(
                detection_confidence=task.get("detection_confidence", 1.0),
                extraction_completeness=0.75 if task.get("assignee") else 0.5,
                assignment_confidence=1.0 if task.get("assignee") else 0.5,
                deadline_confidence=1.0 if task.get("deadline") else 0.6,
            )
            
            task_copy = task.copy()
            task_copy["confidence"] = confidence
            scored_tasks.append(task_copy)
        
        return scored_tasks
