# Step 4: Decision Summarization — Design & Implementation

## Summary

STEP 4 takes decision clusters from STEP 3 and converts each cluster into a **concise, action-oriented decision statement** suitable for a task card. These summaries feed into STEP 5 (task generation).

The module uses a **hybrid approach**:

| Cluster Type | Method | Quality |
|-------------|--------|---------|
| Single-sentence | Rule-based cleaning | ✓ Fast and reliable |
| Multi-sentence | Model summarization + quality gate + fallback | ✓ Always produces clean output |

---

## Input / Output

### Input (from STEP 3)

```
data/decision_clusters/meeting1_clusters.json
```

```json
[
  {"cluster_id": 0, "sentences": [4, 9], "texts": ["I think we should focus on the payment API first", "also we need to finalize the pricing model"], "speakers": ["B", "B"]},
  {"cluster_id": 1, "sentences": [18], "texts": ["let's aim for next wednesday"], "speakers": ["A"]},
  {"cluster_id": 2, "sentences": [6], "texts": ["we need to deploy it by end of march."], "speakers": ["A"]},
  {"cluster_id": 3, "sentences": [15], "texts": ["I will also prepare the documentation"], "speakers": ["C"]},
  {"cluster_id": 4, "sentences": [7], "texts": ["can you prepare the technical spec?"], "speakers": ["A"]}
]
```

### Output

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

---

## Architecture

```
STEP 3 output (decision clusters)
        │
        ▼
┌──────────────────────────────────────────┐
│  For each cluster:                       │
│                                          │
│  Single-sentence?                        │
│  ├─ YES → Rule-based cleaning            │
│  └─ NO  → Clean each sentence            │
│           ├─ Model summarization          │
│           ├─ Quality gate check           │
│           ├─ PASS → Clean model output    │
│           └─ FAIL → Select best sentence  │
│                                          │
│  Post-processing:                        │
│  ├─ Remove conversational prefixes       │
│  ├─ Remove filler words                  │
│  ├─ Resolve pronouns                     │
│  ├─ Capitalize days/months               │
│  └─ Format: capital verb + period        │
└──────────────────┬───────────────────────┘
                   │
                   ▼
            Summary JSON
```

---

## Processing Steps

### 1. Conversational Prefix Removal

Removes 19 conversational patterns anchored at the start of text:

```
"I think we should focus on the API"  → "focus on the API"
"can you prepare the spec?"           → "prepare the spec"
"let's aim for next wednesday"        → "aim for next wednesday"
"I will also prepare the docs"        → "prepare the docs"
"also we need to finalize pricing"    → "finalize pricing"
"maybe we should reconsider"          → "reconsider"
```

Patterns are applied in order from longest to shortest to prevent partial matches.

### 2. Filler Word Removal

Removes words that add no actionable meaning:

| Filler | Example Before | Example After |
|--------|---------------|---------------|
| first | "focus on the API first" | "focus on the API" |
| just | "just deploy it" | "deploy it" |
| actually | "actually finish the report" | "finish the report" |
| basically | "basically rewrite the module" | "rewrite the module" |
| probably | "probably deploy tomorrow" | "deploy tomorrow" |
| definitely | "definitely ship it" | "ship it" |
| kind of / sort of | "kind of redesign it" | "redesign it" |

Uses word-boundary regex (`\b`) to avoid partial word matches.

### 3. Pronoun Resolution

Replaces common unresolved pronouns with generic nouns:

| Pronoun | Replacement | Example |
|---------|-------------|---------|
| it | the system | "deploy it" → "deploy the system" |
| them | the items | "review them" → "review the items" |
| this | the task | "finalize this" → "finalize the task" |

This is a conservative approach — pronouns are replaced with sensible defaults rather than attempting full coreference resolution.

### 4. Date and Day Capitalization

Ensures proper nouns for days and months are capitalized:

```
"next wednesday"  → "next Wednesday"
"end of march"    → "end of March"
"by friday"       → "by Friday"
```

All 7 days and 12 months are covered.

### 5. Final Formatting

- First letter capitalized (typically the action verb)
- Trailing question marks removed
- Exactly one trailing period added
- Multiple spaces collapsed

---

## Multi-Sentence Strategy

For clusters with 2+ sentences, a three-phase approach is used:

### Phase 1: Individual Cleaning

Each sentence in the cluster is cleaned independently through the full pipeline. This ensures conversational prefixes embedded in any sentence are removed.

```
Input:  ["I think we should focus on the payment API first",
         "also we need to finalize the pricing model"]
Cleaned: ["Focus on the payment API.",
          "Finalize the pricing model."]
```

### Phase 2: Model Summarization (if available)

The combined raw texts are fed to `distilbart-cnn-12-6` for abstractive summarization. The output is checked by a **quality gate**:

- **Reject** if model output is ≥80% of combined input length (near-verbatim copy)
- **Reject** if model output contains multiple sentences

This is necessary because `distilbart-cnn-12-6` is trained on long news articles and tends to copy short meeting inputs verbatim.

### Phase 3: Fallback Selection

If the model is unavailable or its output is rejected, the **longest cleaned sentence** is selected as the representative summary. Length serves as a proxy for information content.

```
Cleaned: ["Focus on the payment API.",          ← selected (longer)
          "Finalize the pricing model."]
```

---

## Model Details

### Summarization Model

| Property | Value |
|----------|-------|
| Model | `sshleifer/distilbart-cnn-12-6` |
| Size | ~1.2 GB |
| Architecture | Distilled BART (12 encoder, 6 decoder layers) |
| Training | CNN/DailyMail news summarization |
| Device | CPU (Apple Silicon safe) |

### Generation Parameters

```python
model.generate(
    max_length=60,        # Short output for task statements
    min_length=5,         # Avoid degenerate empty outputs
    num_beams=4,          # Beam search for quality
    length_penalty=1.0,   # Neutral length preference
    early_stopping=True,  # Stop when all beams finish
    no_repeat_ngram_size=3,  # Prevent repetition
)
```

### Apple Silicon Compatibility

```python
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)
device = torch.device("cpu")
```

---

## Improvement Journey

### v1 — Original Implementation

**Problems:**
1. Multi-sentence clusters produced broken concatenations
2. Conversational prefix cleaning only applied at start of combined output
3. No filler word removal
4. No pronoun resolution
5. No date/day capitalization

**Example failure (Cluster 0):**
```
Input:  ["I think we should focus on the payment API first",
         "also we need to finalize the pricing model"]
Output: "Focus on the payment API first . also we need to finalize the pricing model."
```

### v2 — Current Implementation

**Fixes applied:**
1. **Individual sentence cleaning** — each sentence in multi-sentence clusters cleaned separately before combining
2. **Quality gate** — model output checked for near-verbatim copying; rejected outputs fall back to best-sentence selection
3. **Filler word removal** — "first", "just", "actually", etc. stripped
4. **Pronoun resolution** — "it" → "the system", "them" → "the items"
5. **Date capitalization** — all days/months properly capitalized

**Result (Cluster 0):**
```
Input:  ["I think we should focus on the payment API first",
         "also we need to finalize the pricing model"]
Output: "Focus on the payment API."
```

---

## Usage

### Command Line

```bash
python -m pipeline.summarization
# or
python pipeline/summarization.py
```

### Example Script

```bash
python example_summarization.py
```

### Programmatic

```python
from pipeline.summarization import (
    DecisionSummarizer,
    summarize_decisions_in_transcript,
)

# End-to-end
summaries = summarize_decisions_in_transcript(
    input_path="data/decision_clusters/meeting1_clusters.json",
    output_path="data/decision_summaries/meeting1_decisions.json",
)

# Or step by step
summarizer = DecisionSummarizer()
summary = summarizer.summarize_cluster({
    "cluster_id": 0,
    "sentences": [4],
    "texts": ["I think we should focus on the payment API first"],
    "speakers": ["B"],
})
print(summary["summary"])  # "Focus on the payment API."
```

### Tests

```bash
python test_summarization.py
```

---

## Summary Quality Rules

All generated summaries must follow these rules:

1. **One sentence only** — no internal periods or multiple statements
2. **Action-oriented** — starts with an imperative verb
3. **No conversational language** — no "I think", "we should", "let's", etc.
4. **No filler words** — no "first", "just", "actually", etc.
5. **Proper capitalization** — days, months, first letter
6. **Proper punctuation** — ends with exactly one period, no question marks
7. **No hallucination** — summary content must come from input sentences
8. **Pronouns resolved** — common pronouns replaced with generic nouns

### Examples

| ✓ Correct | ✗ Incorrect |
|-----------|------------|
| Focus on the payment API. | I think we should focus on the API. |
| Finalize the pricing model. | Maybe finalize the pricing model. |
| Prepare the documentation. | Discussion about documentation. |
| Deploy the system by end of March. | Deploy it by end of march. |
| Aim for next Wednesday. | let's aim for next wednesday |

---

## Pipeline Position

```
1. 📄 Step 1: Preprocessing           → Raw text → structured sentences
2. 🔍 Step 2: Decision Detection      → Identify decision sentences
3. 📊 Step 3: Clustering              → Group into decision clusters
4. 📝 Step 4: Summarization (this)    → Concise decision statements   ← YOU ARE HERE
5. ✅ Step 5: Task Generation          → Convert to task cards
6. 🖥  Step 6: Display                 → Show on board with evidence
```

---

## Files

| File | Purpose |
|------|---------|
| `pipeline/summarization.py` | Core summarization module |
| `example_summarization.py` | Example usage script |
| `test_summarization.py` | Test suite |
| `data/decision_clusters/meeting1_clusters.json` | Input (from STEP 3) |
| `data/decision_summaries/meeting1_decisions.json` | Output |
| `documentation/STEP4_SUMMARIZATION.md` | This documentation |
