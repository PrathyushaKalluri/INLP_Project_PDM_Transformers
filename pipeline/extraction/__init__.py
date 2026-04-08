"""Extraction module for task metadata."""

from .assignee import AssigneeExtractor
from .deadline import DeadlineExtractor

__all__ = ["AssigneeExtractor", "DeadlineExtractor"]
