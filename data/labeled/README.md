# Gold-Standard Annotations

This directory contains human-annotated task and decision data for evaluation.

## Format

### Task Annotations: `{meeting_id}_tasks_gold.json`

Gold-standard tasks for a meeting, validated by human annotators.

**Schema:**
```json
[
  {
    "task": "Complete OAuth integration implementation",
    "assignee": "Alice",
    "deadline": "tomorrow",
    "priority": "high",
    "source_sentence": "We need to finish the OAuth integration by tomorrow.",
    "meeting_id": "meeting1",
    "annotator_id": "annotator_1",
    "confidence": 1.0
  }
]
```

**Fields:**
- `task`: Task description (required)
- `assignee`: Responsible person (optional, null if N/A)
- `deadline`: Due date in natural language (optional)
- `priority`: Priority level - "low", "medium", "high" (optional)
- `source_sentence`: Original sentence containing the task
- `meeting_id`: Source meeting identifier
- `annotator_id`: Human annotator ID
- `confidence`: Human confidence (1.0 = definite task)

### Decision Annotations: `{meeting_id}_decisions_gold.json`

Gold-standard decisions extracted from meetings.

**Schema:**
```json
[
  {
    "decision": "Approve the new authentication system design",
    "speaker": "Alice",
    "timestamp": "00:15:30",
    "vote_result": "unanimous",
    "source_sentence": "Let's go with the OAuth approach for authentication.",
    "meeting_id": "meeting1",
    "annotator_id": "annotator_1",
    "confidence": 1.0
  }
]
```

**Fields:**
- `decision`: Decision statement (required)
- `speaker`: Person who made the decision (optional)
- `timestamp`: Time in meeting (optional)
- `vote_result`: "unanimous", "majority", "minority", or null
- `source_sentence`: Original sentence
- `meeting_id`: Source meeting
- `annotator_id`: Human annotator
- `confidence`: Human confidence (1.0 = definite decision)

## Annotation Guidelines

### Task Criteria

A task must meet ALL criteria:
1. **Actionable**: Describes a concrete action (verb + object)
2. **Assigned**: Could be assigned to a responsible party
3. **Scoped**: Has clear scope and boundaries
4. **Verifiable**: Success/completion can be determined

**Examples:**
- ✅ "Implement user profile page UI"
- ✅ "Schedule team meeting for next Monday"
- ❌ "The project is complex" (not actionable)
- ❌ "Code review" (too vague without context)

### Decision Criteria

A decision must meet any of:
1. **Explicit**: "We decided to...", "Let's go with...", "Approved the..."
2. **Consensus**: Group agrees on a course of action
3. **Action-binding**: Commits resources or changes direction
4. **Vote-based**: Formal voting occurred

**Examples:**
- ✅ "Use Postgres instead of MySQL"
- ✅ "Push launch date to next month"
- ❌ "We discussed database options" (not a decision)

## Evaluation Protocol

1. **Inter-annotator Agreement**: Compute Cohen's kappa ≥ 0.70
2. **Conflict Resolution**: Third annotator resolves disagreements
3. **Gold Set Creation**: Merge to create single gold annotation
4. **Metrics**: Precision, Recall, F1-score against pipeline predictions

## Directory Structure

```
data/labeled/
├── README.md                        # This file
├── meeting1_tasks_gold.json         # Gold task annotations
├── meeting1_decisions_gold.json     # Gold decision annotations
├── meeting2_tasks_gold.json
├── meeting2_decisions_gold.json
└── annotation_stats.json            # Metadata about annotations
```

## Annotation Stats: `annotation_stats.json`

```json
{
  "total_meetings": 10,
  "total_tasks": 150,
  "avg_tasks_per_meeting": 15,
  "total_decisions": 75,
  "avg_decisions_per_meeting": 7.5,
  "inter_annotator_agreement": {
    "tasks_kappa": 0.82,
    "decisions_kappa": 0.78
  },
  "annotation_date": "2024-12-01"
}
```

## Creating New Annotations

1. **Prepare Meeting Transcript**: Place in `data/raw/`
2. **Run Pipeline**: Generate initial predictions
3. **Manual Review**: Compare predictions against gold criteria
4. **Create JSON**: Format as task/decision JSON files
5. **Validate Schema**: Ensure all required fields present
6. **Commit**: Add to data/labeled/ folder

## Using Gold Annotations

```python
from evaluation import Evaluator

evaluator = Evaluator(gold_annotations_dir="data/labeled")

# Load gold tasks
gold_tasks = evaluator.load_gold_tasks("meeting1")

# Evaluate predictions
results = evaluator.evaluate_tasks(predicted_tasks, "meeting1")
print(f"Precision: {results['extraction_metrics']['precision']}")
print(f"Recall: {results['extraction_metrics']['recall']}")
print(f"F1-Score: {results['extraction_metrics']['f1']}")
```

## Citation

If using these annotations in publications, cite:
> [Project citation info to be added]
