"""Common patterns and regex definitions."""

import re

# Action verbs that indicate task-like statements
ACTION_VERBS = re.compile(
    r"\b(prepare|create|write|send|deploy|build|design|test|review|approve"
    r"|schedule|organize|coordinate|finalize|update|implement|document"
    r"|setup|configure|integrate|optimize|monitor|debug|fix|investigate"
    r"|analyze|research|verify|validate|check|plan|propose|suggest"
    r"|draft|outline|summarize|compile|generate|migrate|refactor|audit"
    r"|handle|improve|run|submit|develop|maintain|prioritize)\b",
    re.I,
)

# Patterns for deadline expressions
DEADLINE_PATTERNS = [
    r"\bby\s+(end\s+of\s+)?(next\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june"
    r"|july|august|september|october|november|december"
    r"|tomorrow|today|week|month|quarter)\b",
    r"\b(next|this)\s+(week|month|quarter)\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]

# Days of week
DAYS_OF_WEEK = {
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday"
}

# Months
MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

# Speaker name pattern (simple heuristic)
SPEAKER_PATTERN = re.compile(r"^[A-Z][a-z]+$")
