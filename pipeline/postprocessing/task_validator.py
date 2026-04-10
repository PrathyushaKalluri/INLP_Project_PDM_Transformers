"""Task validity validation to filter false positive tasks."""

import re
from typing import List, Dict


# Patterns that indicate invalid/non-actionable tasks
INVALID_TASK_PATTERNS = [
    # Metric statements
    r"^\d+\s*%\s*(up|down|growth|decline)",
    r"(revenue|churn|conversion)\s+(is|was)\s+\d+%",
    r"(compared\s+to|went\s+from).*\d+%",
    # Reactions/observations  
    r"^(that'?s|it'?s|things?\s+are)\s+\w+\.$",
    r"^(great|good|cool|interesting|valid)[\.\!\?]*$",
    # Meta questions
    r"^anything\s+else",
    r"^(what|any|do you have)",
    # Exclamations/emotions without action
    r"^(wow|fantastic|awesome|horrible|terrible)[\.\!\?]*$",
    # Meeting scheduling/facilitation (not action items)
    r"\b(meet\s+again|schedule\s+(a\s+)?follow[- ]?up|let'?s\s+meet)\b",
    r"\b(wrap\s+up|let'?s\s+(start|begin|get\s+started|kick\s+off))\b",
    r"\breview\s+progress\b",
]


class TaskValidator:
    """
    Validates tasks to filter out false positives.
    
    Checks:
    - Confidence thresholds (stricter for status meetings)
    - Raw text patterns that are never actionable
    - Manually-review flagged tasks
    """
    
    @staticmethod
    def is_valid_task(task: Dict, meeting_type: str = "mixed") -> bool:
        """
        Determine if a task is valid and should be kept.
        
        Args:
            task (Dict): Task object with keys like 'task', 'confidence', 'evidence', etc.
            meeting_type (str): One of "task_oriented", "status_review", "mixed"
        
        Returns:
            bool: True if task should be kept, False if should be filtered
            
        Examples:
            "We're researching enterprise churn" (confidence 0.79) → True (normal confidence, valid phrasing)
            "Revenue is up 5% compared to last quarter" (confidence 0.80) → False (metric, not actionable)
            "That's great" (confidence 0.82) → False (reaction, not actionable)
        """
        confidence = task.get("confidence", 0.5)
        evidence = task.get("evidence", {})
        raw_text = evidence.get("text", task.get("task", "")).lower()
        
        # Check 1: Reject if confidence too low
        if confidence < 0.5:
            return False
        
        # Check 2: Reject if hard-filtered in detection
        if evidence.get("hard_filtered"):
            return False
        
        # Check 3: Check raw text for invalid patterns
        for pattern in INVALID_TASK_PATTERNS:
            if re.search(pattern, raw_text, re.IGNORECASE):
                return False
        
        # Check 4: Stricter confidence threshold for status meetings
        if meeting_type == "status_review" and confidence < 0.65:
            return False
        
        # Check 5: Stricter confidence for tasks flagged as observations/metrics/consequences
        sentence_type = evidence.get("sentence_type", "general")
        if sentence_type in ("observation", "consequence", "metric"):
            if confidence < 0.75:
                return False
        
        return True
    
    @staticmethod
    def filter_batch(
        tasks: List[Dict],
        meeting_type: str = "mixed",
    ) -> List[Dict]:
        """
        Filter task batch to keep only valid ones.
        
        Args:
            tasks (List[Dict]): List of task objects
            meeting_type (str): Meeting type for context-aware filtering
        
        Returns:
            List[Dict]: Filtered tasks (only valid ones)
        """
        valid_tasks = []
        for task in tasks:
            if TaskValidator.is_valid_task(task, meeting_type):
                valid_tasks.append(task)
        
        return valid_tasks
    
    @staticmethod
    def add_manual_review_flags(tasks: List[Dict]) -> List[Dict]:
        """
        Add manual_review flag to tasks with low confidence.
        
        Tasks with confidence 0.5-0.65 should go to manual review.
        
        Args:
            tasks (List[Dict]): List of task objects
        
        Returns:
            List[Dict]: Tasks with added 'requires_manual_review' field
        """
        flagged_tasks = []
        for task in tasks:
            task_copy = task.copy()
            confidence = task_copy.get("confidence", 0.5)
            
            # Flag for manual review if low-medium confidence
            if 0.5 <= confidence < 0.7:
                task_copy["requires_manual_review"] = True
            
            flagged_tasks.append(task_copy)
        
        return flagged_tasks
