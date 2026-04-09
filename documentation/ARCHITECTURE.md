# Action Extraction Pipeline Architecture

## Overview

The NLP Action Extraction Pipeline is a 4-step modular architecture for extracting actionable tasks from meeting transcripts. Each step is independently testable and produces structured JSON output.

## Pipeline Stages

### Stage 1: Preprocessing
**Purpose**: Prepare raw meeting transcripts for analysis
**Input**: Raw transcript with speaker labels (format: "Speaker: utterance")
**Output**: Cleaned, split sentences with triplet-based confidence scoring

**Components**:
- `parse_speakers()`: Parse speaker labels and utterances
- `split_sentences()`: Split utterances into sentences using spaCy dependency parsing
- `clean_sentences()`: Remove empty or malformed sentences
- `filter_stopwords()`: Remove non-actionable stopword patterns ("ok", "yeah", "hmm", etc.)
- `resolve_triplets()`: Extract Subject-Verb-Object triplets with 9 context-aware fixes
  - Anaphora resolution (track last meaningful object per speaker)
  - Null subject resolution (default to speaker)
  - Let's/we constructions handling
  - Temporal expression filtering
  - Resultative construction handling
  - And more...

**Confidence Scoring**: Triplet extraction confidence (0-1) based on:
- Completeness (subject, verb, object present)
- POS tag validity
- Dependency structure quality
- Contextual flags (anaphora, implied subject, etc.)

**Data Structure**:
```json
[
  {
    "sent_id": "sample_meeting_1_s0",
    "text": "Let's start with sprint planning",
    "speaker": "Alice",
    "tokens": [...],
    "subject": "we",
    "root_verb": "start",
    "object": "sprint planning",
    "triplet_confidence": 0.92,
    "triplet_flags": []
  }
]
```

### Stage 2: Decision Detection
**Purpose**: Identify sentences containing actionable decisions
**Input**: Preprocessed sentences from Stage 1
**Output**: Filtered subset of decision-bearing sentences

**Components**:
- `HybridDetector`: Combines rule-based and transformer-based detection
  - **Rule-based**: Keywords patterns ("decide to", "let's", "we should", etc.)
  - **Transformer-based**: Cross-encoder NLI model for zero-shot classification

**Models**:
- Cross-encoder/nli-distilroberta-base: ~250 MB, threshold=0.85
  - Classifies: ENTAILMENT (decision), NEUTRAL, CONTRADICTION

**Confidence Scoring**: 
- Rule-based: 0.7 (keyword match) or 0.6 (no match)
- Transformer: Raw model confidence (0-1)

**Data Structure**:
```json
[
  {
    "sent_id": "sample_meeting_1_s0",
    "text": "Let's start with sprint planning",
    "speaker": "Alice",
    "tokens": [...],
    "subject": "we",
    "root_verb": "start",
    "object": "sprint planning",
    "triplet_confidence": 0.92,
    "triplet_flags": [],
    "is_decision": true,
    "confidence": 0.92
  }
]
```

### Stage 3: Metadata Extraction
**Purpose**: Extract actionable metadata (assignee, deadline) from decisions
**Input**: Decision sentences from Stage 2
**Output**: Structured task definitions with extracted metadata

**Components**:
- `AssigneeExtractor`: QA model + NER for identifying responsible parties
  - Question template: "Who should do this?"
  - Uses deepset/roberta-base-squad2
  - NER fallback for proper nouns
  
- `DeadlineExtractor`: Temporal expression extraction
  - Identifies deadline phrases ("by Friday", "tomorrow", etc.)
  - Returns normalized deadline string

**Models**:
- deepset/roberta-base-squad2: ~400 MB
  - Extracts answers to custom questions
  - Confidence threshold: 0.5

**Data Structure**:
```json
[
  {
    "raw_text": "Diana, please update the project documentation with the new API specs.",
    "assignee": "Diana",
    "deadline": null,
    "confidence": 0.89,
    "evidence": {
      "text": "Diana, please update the project documentation with the new API specs.",
      "speaker": "Alice"
    }
  }
]
```

**Key Detail**: Raw text preserved for description generation in postprocessing

### Stage 4: Postprocessing
**Purpose**: Build final task objects, generate descriptions, score confidence, remove duplicates
**Input**: Task definitions from Stage 3
**Output**: Final deduplicated task objects with computed confidence

**Components**:

#### 4a. Task Builder
- `TaskBuilder.build_batch()`: Construct task objects
- `TaskDescriptionGenerator`: Generate imperative-form task descriptions
  - Model: google/flan-t5-base (~990 MB)
  - Template: "What is the task? [raw_text]"
  - Fallback: Rule-based capitalization + cleanup
  - Enriches with task_id and metadata

#### 4b. Confidence Scorer
- `ConfidenceScorer.score_batch()`: Compute task-level confidence
- Weighted formula:
  - Decision confidence: 50% (was this really a decision?)
  - Extraction completeness: 20% (all metadata present?)
  - Assignee extraction: 15% (confidence in assignee?)
  - Deadline extraction: 15% (confidence in deadline?)

#### 4c. Deduplicator
- `Deduplicator.deduplicate()`: Remove semantic duplicates
- Method: Embeddings-based cosine similarity
  - Model: sentence-transformers/all-mpnet-base-v2 (~420 MB)
  - Threshold: 0.8 cosine similarity
  - Strategy: Keep highest-confidence version when duplicates found

**Data Structure (Final Output)**:
```json
[
  {
    "task_id": "task_0",
    "task": "Update the project documentation with the new API specifications.",
    "assignee": "Diana",
    "deadline": null,
    "confidence": 0.873,
    "extraction_confidence": 0.89,
    "assignment_confidence": 0.95,
    "deadline_confidence": 0.0,
    "evidence": {
      "text": "Diana, please update the project documentation with the new API specs.",
      "speaker": "Alice"
    },
    "flags": []
  }
]
```

## Data Flow Diagram

```
Raw Transcript
    ↓
[1. PREPROCESSING]
  ├─ parse_speakers
  ├─ split_sentences
  ├─ clean_sentences
  ├─ filter_stopwords
  └─ resolve_triplets (confidence scoring)
    ↓
[2. DECISION DETECTION]
  ├─ HybridDetector
  │  ├─ Rule-based patterns
  │  └─ Cross-encoder NLI
    ↓
[3. METADATA EXTRACTION]
  ├─ AssigneeExtractor (QA + NER)
  └─ DeadlineExtractor (temporal parsing)
    ↓
[4. POSTPROCESSING]
  ├─ TaskBuilder (includes description generation)
  ├─ ConfidenceScorer (weighted fusion)
  └─ Deduplicator (semantic similarity)
    ↓
Final Tasks (JSON)
```

## File Organization

```
pipeline/
├── __init__.py
├── config.py                    # Centralized configuration
├── pipeline.py                  # Orchestrator class
├── preprocessing/
│   ├── __init__.py
│   ├── speaker_parsing.py       # Parser for speaker labels
│   ├── sentence_splitting.py    # spaCy-based splitting
│   ├── cleaning.py              # Text normalization
│   ├── stopword_filtering.py    # Non-actionable removal
│   └── triplet_resolver.py      # S-V-O extraction + confidence
├── detection/
│   ├── __init__.py
│   └── detector.py              # Hybrid rule + transformer detection
├── extraction/
│   ├── __init__.py
│   ├── assignee.py              # QA + NER for assignees
│   └── deadline.py              # Temporal expression extraction
└── postprocessing/
    ├── __init__.py
    ├── task_builder.py          # Task construction + description generation
    ├── confidence.py            # Confidence scoring
    └── deduplication.py         # Semantic deduplication
```

## Model Architecture

### Models Used

| Stage | Component | Model | Size | Threshold |
|-------|-----------|-------|------|-----------|
| 1 | Sentence Splitting | spaCy en_core_web_sm | 40 MB | N/A |
| 2 | Decision Detection | cross-encoder/nli-distilroberta-base | 250 MB | 0.85 |
| 3 | Metadata Extraction | deepset/roberta-base-squad2 | 400 MB | 0.5 |
| 4 | Description Gen | google/flan-t5-base | 990 MB | N/A |
| 4 | Deduplication | all-mpnet-base-v2 | 420 MB | 0.8 |

**Total Memory**: ~2.1 GB (models cached locally)

### Model Loading Strategy
- **Lazy Loading**: Models loaded only when needed (reduces startup time)
- **Caching**: Models cached by HuggingFace Hub utilities (~/.cache/)
- **Singleton Pattern**: Embedder reused across deduplication operations

## Configuration

All settings centralized in `pipeline/config.py`:

```python
# Feature flags
USE_TRANSFORMER_CLASSIFIER = True       # Enable zero-shot NLI
USE_RULE_BASED_DETECTION = True         # Enable keyword patterns

# Models
NLI_MODEL = "cross-encoder/nli-distilroberta-base"
QA_MODEL = "deepset/roberta-base-squad2"
SUMMARIZATION_MODEL = "google/flan-t5-base"
EMBEDDING_MODEL = "all-mpnet-base-v2"

# Thresholds
DECISION_THRESHOLD = 0.85               # Min confidence to keep decision
DEDUPLICATION_THRESHOLD = 0.8           # Cosine similarity threshold

# Data directories
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
OUTPUT_DATA_DIR = "data/outputs"
LABELED_DATA_DIR = "data/labeled"
```

## Usage

### Via run_pipeline.py (Main Entry Point)

```bash
# From file
python run_pipeline.py transcripts/meeting.txt

# From stdin
python run_pipeline.py

# Output files:
# - data/processed/{meeting_id}.json                  (Step 1)
# - data/processed/{meeting_id}_decisions.json        (Step 2)
# - data/processed/{meeting_id}_extractions.json      (Step 3)
# - data/outputs/{meeting_id}_tasks.json              (Step 4)
```

### Via pipeline.py (Programmatic API)

```python
from pipeline import NLPActionExtractor

extractor = NLPActionExtractor()
tasks = extractor.run_pipeline(transcript_text)

for task in tasks:
    print(f"{task['task']} → {task['assignee']} ({task['confidence']:.0%})")
```

### Via Evaluation Framework

```python
from evaluation import Evaluator

evaluator = Evaluator(gold_annotations_dir="data/labeled")
results = evaluator.evaluate_tasks(predicted_tasks, "meeting1")
print(f"F1-Score: {results['extraction_metrics']['f1']:.3f}")
```

## Performance Characteristics

| Stage | Complexity | Memory | Time |
|-------|-----------|--------|------|
| 1. Preprocessing | O(n) | ~100 MB | ~1s |
| 2. Detection | O(n·m) | ~500 MB | ~3s |
| 3. Extraction | O(n·k) | ~800 MB | ~5s |
| 4. Postprocessing | O(n²) | ~600 MB | ~8s |
| **Total** | — | ~2.1 GB | ~17s |

*Per typical meeting (n=100 sentences, m=detection candidates, k=extracted metadata)*

## Future Improvements

1. **Fine-tuning**: Train models on domain-specific meeting data
2. **Coreference Resolution**: Better anaphora handling in Stage 1
3. **Temporal Normalization**: Convert "Friday" → structured date format
4. **Dialogue Acts**: Identify question, request, commitment speech acts
5. **Multi-turn Actions**: Track action dependencies across discussion turns
6. **Interactive Refinement**: User feedback loop for model correction

## References

- **Sentence Segmentation**: Reimers & Gurevych (2019) on sentence splitting strategies
- **Task Detection**: Zero-shot NLI following Yin et al. (2019)
- **Semantic Similarity**: Reimers & Gurevych (2019) on sentence embeddings
- **Triplet Extraction**: Stanford dependency-based techniques (de Marneffe et al., 2008)

## Related Documentation

- [README.md](../README.md) - Project overview
- [data/labeled/README.md](../data/labeled/README.md) - Annotation format
- [models/README.md](../models/README.md) - Model management
- [evaluation/README.md](../evaluation/README.md) - Evaluation framework (if exists)
