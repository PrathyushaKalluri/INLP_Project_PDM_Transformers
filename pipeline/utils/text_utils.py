"""Text utility functions."""

import re
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize text: whitespace, case, punctuation.
    
    Args:
        text (str): Raw text
    
    Returns:
        str: Normalized text
    """
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove extra punctuation
    text = re.sub(r'([.!?])\1+', r'\1', text)
    
    return text


def sanitize_task(task_text: str) -> Optional[str]:
    """
    Clean task description for final output.
    
    Args:
        task_text (str): Raw task text
    
    Returns:
        str: Sanitized task or None
    """
    if not task_text:
        return None
    
    sanitized = normalize_text(task_text)
    
    # Remove leading/trailing punctuation
    sanitized = sanitized.strip('\'".,;:!?-')
    
    if len(sanitized.split()) < 3:
        return None
    
    return sanitized


def extract_names(text: str) -> list:
    """
    Extract potential names from text.
    
    Args:
        text (str): Text to extract from
    
    Returns:
        list: Potential names
    """
    # Simple heuristic: capitalized words
    words = text.split()
    names = [w.rstrip(',:;.!?') for w in words if w and w[0].isupper() and len(w) > 1]
    return list(set(names))
