# Evaluation Methodology

**Project:** PDM Transformers — Meeting Action Extraction  
**Version:** 2.0  
**Last Updated:** April 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [What is Being Evaluated?](#2-what-is-being-evaluated)
3. [Gold Standard Annotations](#3-gold-standard-annotations)
   - 3.1 Format
   - 3.2 Annotation Principles
   - 3.3 The Six Sample Meetings
4. [Evaluation Metrics](#4-evaluation-metrics)
   - 4.1 Precision
   - 4.2 Recall
   - 4.3 F1-Score
   - 4.4 Extraction Quality Metrics
5. [Matching Methods](#5-matching-methods)
   - 5.1 Exact Match
   - 5.2 Partial (Fuzzy) Match
   - 5.3 Semantic Match
6. [Evaluation Framework](#6-evaluation-framework)
   - 6.1 `test_all_meetings.py` — End-to-End Evaluation
   - 6.2 `evaluation/evaluate.py` — Formal Evaluator Class
   - 6.3 `evaluation/metrics.py` — Metrics Calculator
7. [Per-Meeting Expected Outcomes](#7-per-meeting-expected-outcomes)
8. [How to Run Evaluation](#8-how-to-run-evaluation)
9. [Interpreting Results](#9-interpreting-results)
10. [Limitations of the Current Evaluation Setup](#10-limitations-of-the-current-evaluation-setup)

---

## 1. Overview

Evaluation of this pipeline is framed as an **information extraction** task. Given a transcript with a known set of ground-truth action items (the *gold standard*), we measure how many the pipeline correctly identifies (recall), how many of its predictions are actually valid tasks (precision), and the harmonic mean of the two (F1).

There are two layers of evaluation:

| Layer | What it measures | Where it runs |
|-------|-----------------|---------------|
| **Task extraction** | Are the final output tasks correct? | `test_all_meetings.py`, `evaluation/evaluate.py` |
| **Decision detection** | Did Stage 2 detect the right sentences? | `evaluation/evaluate.py` (`evaluate_decisions`) |

The primary reported metric is **end-to-end task extraction** performance — what matters to the end user is the quality of the final task list, not internal intermediate accuracy.

---

## 2. What is Being Evaluated?

The pipeline output is a list of structured task objects. Evaluation compares the **evidence text** of each extracted task against gold-standard sentences to determine whether a task was a true positive.

Specifically, for evaluation in `test_all_meetings.py`, matching is done on the `evidence.text` field — the original sentence from the transcript that the task was derived from. This is the most reliable matching key because:

- Task titles are generated/paraphrased (they change wording), so exact title matching would systematically undercount true positives.
- The evidence text is always a direct substring of the original transcript, making normalised comparison tractable.

For the formal `Evaluator` class in `evaluation/evaluate.py`, task titles are matched directly (using exact, partial, or semantic similarity). This is appropriate when gold annotations are structured task objects (not raw sentences).

---

## 3. Gold Standard Annotations

### 3.1 Format

Two types of gold annotations are used:

**Inline annotations** (used by `test_all_meetings.py`):
Hardcoded as a Python dict mapping raw sentence strings to boolean decision flags:

```python
GOLD_STANDARDS = {
    1: {
        "I will handle the API refactor by Friday.": True,   # task
        "Good morning everyone.": False,                      # not a task
        "Let's meet again on Friday to review progress.": False,
    },
    ...
}
```

**File-based annotations** (used by `evaluation/evaluate.py`):
JSON files stored in `data/labeled/`, named `{meeting_id}_tasks_gold.json` and `{meeting_id}_decisions_gold.json`. Each file contains a list of dicts with the same structure as pipeline output.

### 3.2 Annotation Principles

A sentence is annotated as a **task** (True) if it represents:
- A **commitment** by a named person to perform a future action ("I will handle the API refactor by Friday")
- A **directive** assigning work to a named person ("Charlie, can you write the integration tests?")
- A **team-scope decision** ("Let's also follow up on the deployment pipeline issue")
- A **task that was implicitly accepted** through an acceptance response

A sentence is annotated as **not a task** (False) if it is:
- A greeting, farewell, or social nicety
- A status update or observation about past/current state
- A metric or data statement
- A pure question with no actionable answer in context
- A scheduling statement for a future meeting (e.g., "Let's meet again on Friday")
- A reaction or assessment ("That's great", "Sounds good")

### 3.3 The Six Sample Meetings

The test corpus contains six synthetic meeting transcripts, each testing a different meeting pattern:

| Meeting | Type | Focus | Gold Tasks |
|---------|------|-------|-----------|
| `sample_meeting_1.txt` | Sprint planning | API refactoring, tests, docs, CI/CD | 7 |
| `sample_meeting_2.txt` | Performance review | Benchmarking, architecture, load balancer | 5 |
| `sample_meeting_3.txt` | Feature release planning | DB optimisation, APIs, error tracking, migration | 10 |
| `sample_meeting_4.txt` | Incident postmortem | Connection pools, dashboards, circuit breakers, audit | 10 |
| `sample_meeting_5.txt` | Development standup | OAuth, notifications, prototype, demo | 9 |
| `sample_meeting_6.txt` | Quarterly business review | Status meeting with only 3 genuine tasks amid 16+ observations/metrics | 3 |

**Meeting 6 is the critical test case.** It is a status review meeting dominated by metric statements and reactions. A high-quality pipeline should extract only the 3 genuine action items ("We should look into that", "Let's keep monitoring the situation", "Let's maybe revisit the churn issue") while suppressing the surrounding 16+ non-actionable sentences.

---

## 4. Evaluation Metrics

### 4.1 Precision

**"Of all the tasks the pipeline extracted, what fraction were actually tasks?"**

```
Precision = TP / (TP + FP)
```

- **True Positive (TP):** Extracted task whose evidence text matches a gold task sentence
- **False Positive (FP):** Extracted task whose evidence text does not match any gold task
- **High precision** = few spurious tasks; users see only real action items

A pipeline extracting 2 tasks, both correct → Precision = 1.0  
A pipeline extracting 5 tasks, 2 correct, 3 spurious → Precision = 0.40

### 4.2 Recall

**"Of all the true tasks in the meeting, what fraction did the pipeline find?"**

```
Recall = TP / (TP + FN)
```

- **False Negative (FN):** Gold task that was not in the pipeline's output
- **High recall** = few missed tasks; nothing important is lost

A pipeline that finds 2 of 7 gold tasks → Recall = 0.286  
A pipeline that finds 7 of 7 → Recall = 1.0

### 4.3 F1-Score

The harmonic mean of precision and recall. It is the primary single-number metric because it penalises both missed tasks (low recall) and spurious tasks (low precision) equally:

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

Harmonic mean is used (not arithmetic) because it is more sensitive to imbalance: a pipeline with Precision=1.0 and Recall=0.10 gets F1=0.18, not 0.55.

### 4.4 Extraction Quality Metrics

Reported alongside precision/recall in the formal `Evaluator`:

| Metric | Description | Formula |
|--------|-------------|---------|
| **Completeness** | Fraction of tasks with all three required fields (task, assignee, deadline) | `complete / total` |
| **N/A rate** | Fraction of tasks missing at least one required field | `1 - completeness` |
| **Avg confidence** | Mean composite confidence score across all extracted tasks | `sum(conf) / n` |
| **High confidence ratio** | Fraction of decisions with confidence > 0.80 | `high / total` |

Completeness is arguably as important as precision/recall for practical use: a task without an assignee or deadline loses much of its actionability.

---

## 5. Matching Methods

Both `test_all_meetings.py` and the formal `Evaluator` need to decide whether a predicted item matches a gold item. Three methods are available:

### 5.1 Exact Match

Case-insensitive string equality:

```python
predicted.strip().lower() == gold.strip().lower()
```

**Use when:** The pipeline output is expected to reproduce the exact gold string verbatim. Typically not used for generated task titles (which are paraphrased) but is used in Stage 1/2 evaluation where raw sentence text is compared.

### 5.2 Partial (Fuzzy) Match

`difflib.SequenceMatcher` character-level ratio, threshold ≥ 0.7:

```python
SequenceMatcher(None, predicted.lower(), gold.lower()).ratio() >= 0.7
```

**Use when:** Output is expected to be close to the gold string but may have minor surface variations (different capitalisation, punctuation, or light rephrasing).

**Threshold choice:** 0.7 was chosen to tolerate ~30% character difference while still requiring substantial string overlap. For example, "Deploy The API." vs "Deploy the API" scores ≈ 0.93.

### 5.3 Semantic Match

Cosine similarity between sentence embeddings from `all-mpnet-base-v2`, threshold ≥ 0.8:

```python
embedder.encode([predicted, gold])
cosine_similarity(emb1, emb2) >= 0.8
```

**Use when:** Task titles are heavily paraphrased or generated by LLMs, where surface form differs significantly from the gold string. `all-mpnet-base-v2` is specifically designed for semantic similarity tasks.

**Threshold choice:** 0.80 is a standard threshold for sentence-level near-duplicate detection with `all-mpnet-base-v2`, balancing precision (real matches) against noise (coincidentally high-scoring pairs).

**Note:** Both `Deduplicator` and `MetricsCalculator.semantic_match` use the same `all-mpnet-base-v2` model. In the `Deduplicator`, the embedder is cached as a class-level singleton to avoid reloading. In `MetricsCalculator.semantic_match`, a **new model instance is created per call** — this is a known inefficiency when evaluating large outputs.

---

## 6. Evaluation Framework

### 6.1 `test_all_meetings.py` — End-to-End Evaluation

The primary evaluation script. Runs the full pipeline on all 6 sample meetings and computes precision/recall/F1 against the inline gold standard annotations.

**Matching approach:** Evidence text matching (not title matching). Each extracted task's `evidence.text` field is lowercased, stripped, and looked up in the gold standard dict.

**Aggregate metrics:** Global TP/FP/FN counts are accumulated across all 6 meetings, and a single set of micro-averaged precision/recall/F1 is reported alongside per-meeting results.

**Special Meeting 6 check:** The script includes a dedicated check for Meeting 6 (the status meeting). If `extracted_count ≤ 4` and `precision ≥ 0.75`, it prints `[✓] MEETING 6 PASSED`. This acts as a regression guard for false-positive suppression.

```
Usage:
    python test_all_meetings.py
```

**Output format:**
```
MEETING 1: sample_meeting_1.txt
  Extracted tasks:   7
  Gold standard tasks: 7
  True Positives:    6
  False Positives:   1
  False Negatives:   1
  Precision: 0.857 (6/7)
  Recall:    0.857 (6/7)
  F1 Score:  0.857
```

### 6.2 `evaluation/evaluate.py` — Formal Evaluator Class

A reusable `Evaluator` class for structured evaluation against file-based gold annotations.

**Key methods:**

| Method | Description |
|--------|-------------|
| `evaluate_tasks(predicted, meeting_id, match_type)` | Load gold from `data/labeled/{id}_tasks_gold.json`, compute P/R/F1 and quality metrics |
| `evaluate_decisions(predicted, meeting_id)` | Load gold from `data/labeled/{id}_decisions_gold.json`, compute detection-level metrics |
| `evaluate_all_meetings(predictions_dir, match_type)` | Batch evaluate all `*_tasks.json` files in a directory |
| `print_evaluation_report(results)` | Print formatted table of all results |

**Usage:**
```python
from evaluation.evaluate import Evaluator

evaluator = Evaluator(gold_annotations_dir="data/labeled")
results = evaluator.evaluate_all_meetings(
    predictions_dir="data/outputs",
    match_type="semantic"      # "exact", "partial", or "semantic"
)
evaluator.print_evaluation_report(results)
```

**Prerequisites:** Gold annotation files must exist in `data/labeled/`. These are not automatically generated — they must be created manually or from an annotation tool. Currently the sample meeting gold files are not in this directory; evaluation uses the inline annotations in `test_all_meetings.py` instead.

### 6.3 `evaluation/metrics.py` — Metrics Calculator

A stateless utility class with four static methods:

**`extract_metrics(predicted, gold, match_type)`**

Computes TP/FP/FN and derives precision/recall/F1. Uses a *greedy one-to-one matching* strategy: for each predicted task, find the first unmatched gold task that satisfies the match condition. A gold task can only be matched once (prevents artificially inflating TP by matching one prediction against multiple gold items).

```python
MetricsCalculator.extract_metrics(
    predicted_tasks=[{"task": "Deploy the API.", ...}],
    gold_tasks=[{"task": "Deploy the API to production.", ...}],
    match_type="semantic"
)
# Returns: {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 1, "fp": 0, "fn": 0}
```

**`extraction_quality(tasks)`**

Checks completeness (all three required fields present: `task`, `assignee`, `deadline`), N/A rate, and average confidence. Returns quality metrics dict.

**`detection_quality(decisions)`**

For Stage 2 decisions, reports total count, average confidence, and high-confidence ratio (threshold: 0.80).

**`exact_match` / `partial_match` / `semantic_match`**

Static boolean matchers for use in evaluation loops or one-off comparisons.

---

## 7. Per-Meeting Expected Outcomes

These are the target outcomes used to validate pipeline correctness. Precision targets reflect the difficulty and noise level of each meeting type.

| Meeting | Gold Tasks | Primary Challenge | Precision Target | Recall Target |
|---------|-----------|-------------------|-----------------|--------------|
| 1 | 7 | Sprint planning — mostly clear commitments | ≥ 0.80 | ≥ 0.80 |
| 2 | 5 | Performance review — some ambiguous obligations | ≥ 0.75 | ≥ 0.80 |
| 3 | 10 | Large meeting — many tasks, mixed phrasing | ≥ 0.75 | ≥ 0.80 |
| 4 | 10 | Incident postmortem — dense, imperative-heavy | ≥ 0.80 | ≥ 0.85 |
| 5 | 9 | Development standup — past/present/future mixed | ≥ 0.80 | ≥ 0.80 |
| **6** | **3** | **Status meeting — minority task suppression** | **≥ 0.75** | **1.00** |

Meeting 6 is the hardest: only 3 of 19+ sentences are real tasks. High recall is prioritised (we must not miss any of the 3 genuine action items), while precision is relaxed to ≥ 0.75 (up to 1 false positive is acceptable).

---

## 8. How to Run Evaluation

### Quick End-to-End Evaluation

```bash
# From project root
python test_all_meetings.py
```

Runs all 6 meetings, prints per-meeting metrics and a summary table. No additional files needed.

### Single Meeting Test

```bash
python run_pipeline.py transcripts/sample_meeting_1.txt
```

Runs the pipeline on one meeting and prints the extracted tasks to stdout with confidence scores and assignees.

### Formal Evaluation (requires gold annotation files)

```python
from evaluation.evaluate import Evaluator

evaluator = Evaluator(gold_annotations_dir="data/labeled")

# Evaluate a single meeting
results = evaluator.evaluate_tasks(
    predicted_tasks=tasks,           # List of task dicts from pipeline
    meeting_id="sample_meeting_1",
    match_type="semantic"
)

# Evaluate Step 2 detection
decisions = [s for s in detected if s.get("is_decision")]
det_results = evaluator.evaluate_decisions(decisions, "sample_meeting_1")

# Batch evaluation
all_results = evaluator.evaluate_all_meetings("data/outputs", match_type="partial")
evaluator.print_evaluation_report(all_results)
```

### Inspecting Intermediate Outputs

The CLI pipeline (`run_pipeline.py`) saves intermediate JSON for every stage:

| File | Stage | Contents |
|------|-------|----------|
| `data/processed/{id}.json` | Stage 1 | Preprocessed sentences with triplets |
| `data/processed/{id}_decisions.json` | Stage 2 | All sentences with `is_decision` flags and confidence scores |
| `data/processed/{id}_extractions.json` | Stage 3 | Task definitions with assignee/deadline |
| `data/outputs/{id}_tasks.json` | Stage 4 | Final validated task list |

These can be inspected directly to debug any stage of the pipeline independently.

---

## 9. Interpreting Results

### Reading the Precision–Recall Trade-off

The pipeline has several tunable thresholds that shift the precision–recall balance:

| Threshold | Location | Effect of increasing |
|-----------|----------|---------------------|
| `DECISION_THRESHOLD` (`config.py`, default 0.85) | Stage 2 high-zone boundary | Fewer tasks extracted (↑ precision, ↓ recall) |
| `THRESHOLD_REVIEW` (`hybrid_detector.py`, default 0.4) | Stage 2 review-zone lower bound | More tasks filtered (↑ precision, ↓ recall) |
| `DEDUPLICATION_THRESHOLD` (`config.py`, default 0.8) | Stage 4 deduplication | Lower value merges more aggressively (↓ recall risk) |
| `TaskValidator` confidence threshold (default 0.5) | Stage 4 validation | Raising this cuts borderline tasks (↑ precision, ↓ recall) |

### Common Failure Patterns

| Failure | Root Cause | Diagnostic |
|---------|-----------|------------|
| **False positive: observation** | NLI classified a status-update sentence as commitment | Check `confidence_zone` in `_decisions.json`; if "review", reduce modal_boost or raise threshold |
| **False positive: meeting scheduling** | "Let's meet again" not caught by validator | Check `task_validator.py` `INVALID_TASK_PATTERNS` |
| **False negative: implicit commitment** | Speaker accepts a request but doesn't use future tense | Check if `is_turn_pair_acceptance` was set in `_decisions.json` |
| **False negative: weak action verb** | Action verb not in `rule_based.py` ACTION_VERBS | Add verb to the pattern set |
| **Wrong assignee** | Speaker name not in `_known_speakers` | Check `_decisions.json` for `subject` field; verify speakers parsed correctly |
| **Missing deadline** | Deadline phrasing not matched by any pattern | Check `deadline.py` `DEADLINE_PATTERNS` |

### Confidence Score Calibration

Well-calibrated tasks should show:
- **High-confidence tasks (> 0.80):** Clear, future-tense self-commitments with both assignee and deadline found
- **Mid-confidence tasks (0.60–0.80):** Commitments without deadline, or team-level tasks, or requests
- **Low-confidence tasks (0.50–0.60):** Borderline sentences; marked `requires_manual_review=True`

If average confidence across all tasks is consistently above 0.85, the composite scorer may be under-penalising missing fields. If below 0.60, the detection threshold may be set too low.

---

## 10. Limitations of the Current Evaluation Setup

### No Held-Out Test Split
All six sample meetings are used for both development (tuning thresholds and patterns) and evaluation. There is no separate held-out test set, so reported metrics may be optimistically biased. A proper evaluation would require annotating additional unseen transcripts.

### Synthetic Transcripts
The six sample meetings are synthetic — they were written to include clear, well-formed commitments. Real meeting transcripts are noisier, more anaphoric, and contain more ambiguous obligations. Performance on real data will likely be lower.

### Evidence-Text Matching Ambiguity
In `test_all_meetings.py`, matching is done on evidence text (original sentence from transcript). However, when one gold-standard sentence generates multiple tasks through the pipeline (e.g., via triplet decomposition), only the first match is counted. This can undercount true positives in a few edge cases.

### No Span-Level Deadline/Assignee Evaluation
Precision and recall only measure whether the *sentence* was correctly identified as a task. There is no separate metric for whether the assignee was correctly extracted or whether the deadline exactly matches. A pipeline that correctly identifies all tasks but systematically misidentifies assignees would receive a perfect F1 score under the current evaluation.

### Single-Model Evaluation for Semantic Matching
`MetricsCalculator.semantic_match` instantiates a new `SentenceTransformer` object on every call. When evaluating many task pairs this creates significant overhead. For batch evaluation, the embedder should be instantiated once and reused.

### No Cross-Validation
The six meetings represent a hand-curated set, not a statistically meaningful sample. Reported aggregate F1 should be interpreted as a functional capability indicator, not as a generalisable performance estimate.
