# Step 5: Task Generation — Design & Implementation

## Summary

STEP 5 converts decision summaries from STEP 4 into **structured task objects** with ML-extracted metadata. Each task includes a title, assignee, deadline, evidence links, and cluster reference. These tasks feed into STEP 6 (board display).

The module uses **two ML models** for metadata extraction:

| Extraction | Model | Fallback |
|-----------|-------|----------|
| Assignee | QA: `deepset/roberta-base-squad2` | Speaker-based heuristics |
| Deadline | NER: spaCy `en_core_web_sm` | Regex date pattern matching |

---

## Input / Output

### Input (from STEP 4 + STEP 1)

**Decision summaries:**
```
data/decision_summaries/meeting1_decisions.json
```

```json
[
  {"cluster_id": 0, "summary": "Focus on the payment API.", "evidence_sentences": [4, 9]},
  {"cluster_id": 1, "summary": "Aim for next Wednesday.", "evidence_sentences": [18]},
  {"cluster_id": 2, "summary": "Deploy the system by end of March.", "evidence_sentences": [6]},
  {"cluster_id": 3, "summary": "Prepare the documentation.", "evidence_sentences": [15]},
  {"cluster_id": 4, "summary": "Prepare the technical spec.", "evidence_sentences": [7]}
]
```

**Transcript sentences (for speaker context):**
```
data/processed_transcripts/meeting1.json
```

### Output

```
data/tasks/meeting1_tasks.json
```

```json
[
  {"task_id": 0, "title": "Focus on the payment API", "assignee": "B", "deadline": null, "evidence_sentences": [4, 9], "cluster_id": 0},
  {"task_id": 1, "title": "Aim for next Wednesday", "assignee": "A", "deadline": "next Wednesday", "evidence_sentences": [18], "cluster_id": 1},
  {"task_id": 2, "title": "Deploy the system by end of March", "assignee": "A", "deadline": "end of March", "evidence_sentences": [6], "cluster_id": 2},
  {"task_id": 3, "title": "Prepare the documentation", "assignee": "C", "deadline": null, "evidence_sentences": [15], "cluster_id": 3},
  {"task_id": 4, "title": "Prepare the technical spec", "assignee": "A", "deadline": null, "evidence_sentences": [7], "cluster_id": 4}
]
```

---

## Architecture

```
STEP 4 output (decision summaries)     STEP 1 output (transcript)
        │                                       │
        ▼                                       ▼
┌───────────────────────────────────────────────────────┐
│  For each summary:                                    │
│                                                       │
│  1. Retrieve evidence sentences from transcript       │
│  2. Build context: "Speaker: text" format             │
│                                                       │
│  ┌─────────────────┐    ┌──────────────────────┐      │
│  │  QA Model        │    │  NER Model            │     │
│  │  roberta-squad2  │    │  spaCy en_core_web_sm │     │
│  │                  │    │                        │     │
│  │  Question:       │    │  Detect entities:      │     │
│  │  "Who is         │    │  DATE, TIME            │     │
│  │  responsible?"   │    │                        │     │
│  └────────┬─────────┘    └───────────┬────────────┘    │
│           │                          │                 │
│           ▼                          ▼                 │
│      Assignee                    Deadline              │
│  (name or speaker)          (temporal expr)            │
│                                                       │
│  3. Construct task object                             │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
                      Tasks JSON
```

---

## Task Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | int | Task identifier (same as cluster_id) |
| `title` | str | Action title from summary (no trailing period) |
| `assignee` | str | Person responsible (name or speaker label) |
| `deadline` | str \| null | Temporal expression, or null if none detected |
| `evidence_sentences` | list[int] | Transcript sentence IDs supporting this task |
| `cluster_id` | int | Link back to decision cluster |

---

## ML Models

### Question Answering — Assignee Extraction

| Property | Value |
|----------|-------|
| Model | `deepset/roberta-base-squad2` |
| Size | ~500 MB |
| Architecture | RoBERTa base fine-tuned on SQuAD 2.0 |
| Input | Question + evidence context |
| Output | Answer span (person name or speaker label) |
| Device | CPU (Apple Silicon safe) |

**How it works:**

The QA model receives:
- **Question:** `"Who is responsible for performing this task?"`
- **Context:** `"Task: Prepare the technical spec. Context: A: can you prepare the technical spec?"`

The model extracts the answer span from the context, identifying the person responsible.

**SQuAD 2.0 advantage:** This model can output "no answer" when no assignee is explicitly mentioned, avoiding hallucination. When the model returns no answer, the system falls back to speaker-based extraction.

### Named Entity Recognition — Deadline Extraction

| Property | Value |
|----------|-------|
| Model | spaCy `en_core_web_sm` |
| Size | ~12 MB |
| Entity types | DATE, TIME |
| Input | Summary text + evidence texts |
| Output | First temporal entity found |

**How it works:**

spaCy NER processes the summary and evidence texts, extracting entities labeled `DATE` or `TIME`:

```
"Deploy the system by end of March."
→ Entity: "end of March" (DATE)

"Aim for next Wednesday."
→ Entity: "next Wednesday" (DATE)
```

---

## Fallback Strategies

### Assignee Fallback (when QA model unavailable)

A rule-based strategy using linguistic patterns:

1. **Self-assignment:** If evidence text contains "I will", "I'll", "I can", "let me" → the speaker is the assignee
2. **Delegation:** If evidence text contains "can you", "could you" → the speaker (delegator) is recorded as the task owner
3. **Default:** Speaker of the first evidence sentence

| Pattern | Example | Assignee |
|---------|---------|----------|
| Self-assignment | `"C: I will prepare the documentation"` | C |
| Delegation | `"A: can you prepare the technical spec?"` | A |
| Default | `"B: I think we should focus on the API"` | B |

### Deadline Fallback (when spaCy unavailable)

Regex patterns matching common temporal expressions:

| Pattern | Examples |
|---------|---------|
| `by + date` | "by end of March", "by Friday", "by tomorrow" |
| `next + day/period` | "next Wednesday", "next week", "next month" |
| `end of + period` | "end of March", "end of the month" |
| `Month + day` | "March 15", "January 3" |
| Relative | "tomorrow", "today" |

---

## Processing Logic

For each decision summary:

```
1. Look up evidence sentence IDs in transcript
   → Get full sentence text + speaker metadata

2. Build QA context string:
   "Task: {summary} Context: {speaker}: {text} ..."

3. Run QA model:
   Q: "Who is responsible for performing this task?"
   A: extracted assignee (or fallback to speaker)

4. Run NER on summary text:
   → Extract DATE/TIME entities → deadline

5. If no deadline in summary, search evidence texts

6. Strip trailing period from summary → title

7. Construct task object with all fields
```

---

## Edge Cases

### No assignee detected

When both QA model and pattern matching fail:
- Falls back to speaker of first evidence sentence
- If no evidence sentences found: returns `"Unknown"`

### Missing evidence sentence

When evidence sentence IDs don't exist in transcript:
- Task is still created with empty evidence context
- Assignee defaults to `"Unknown"`

### No deadline

When no temporal expression is found in summary or evidence:
- `deadline` is set to `null`
- This is correct — not all tasks have explicit deadlines

### Multiple evidence sentences

Evidence sentences are concatenated into a single context string:
```
"B: I think we should focus on the payment API first B: also we need to finalize the pricing model"
```
The QA model processes the full context to determine the assignee.

---

## Usage

### Command Line

```bash
python -m pipeline.task_generator
# or
python pipeline/task_generator.py
```

### Example Script

```bash
python example_task_generation.py
```

### Programmatic

```python
from pipeline.task_generator import (
    TaskGenerator,
    generate_tasks_from_transcript,
)

# End-to-end
tasks = generate_tasks_from_transcript(
    summaries_path="data/decision_summaries/meeting1_decisions.json",
    transcript_path="data/processed_transcripts/meeting1.json",
    output_path="data/tasks/meeting1_tasks.json",
)

# Or step by step
generator = TaskGenerator()
task = generator.generate_task(
    summary={"cluster_id": 0, "summary": "Focus on the API.", "evidence_sentences": [4]},
    transcript_sentences=[{"sentence_id": 4, "speaker": "B", "text": "focus on the API"}],
)
print(task)
```

### Tests

```bash
python test_task_generation.py
```

---

## Pipeline Position

```
1. 📄 Step 1: Preprocessing           → Raw text → structured sentences
2. 🔍 Step 2: Decision Detection      → Identify decision sentences
3. 📊 Step 3: Clustering              → Group into decision clusters
4. 📝 Step 4: Summarization           → Concise decision statements
5. ✅ Step 5: Task Generation (this)   → Structured task objects       ← YOU ARE HERE
6. 🖥  Step 6: Display                 → Show on board with evidence
```

---

## Files

| File | Purpose |
|------|---------|
| `pipeline/task_generator.py` | Core task generation module |
| `example_task_generation.py` | Example usage script |
| `test_task_generation.py` | Test suite |
| `data/decision_summaries/meeting1_decisions.json` | Input (from STEP 4) |
| `data/processed_transcripts/meeting1.json` | Input (from STEP 1) |
| `data/tasks/meeting1_tasks.json` | Output |
| `documentation/STEP5_TASK_GENERATION.md` | This documentation |
