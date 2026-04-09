# Meeting Action Extractor - NLP Pipeline

Automatic extraction of action items from meeting transcripts using transformers and NLP.

## ⚡ Quick Start

```bash
# Extract tasks from a meeting transcript
python run_pipeline.py transcripts/sample_meeting_1.txt

# Or paste from stdin
python run_pipeline.py
# Paste transcript, then press CTRL+D
```

## Pipeline Overview

The 4-step pipeline automatically extracts actionable tasks from meeting transcripts:

```
Raw Transcript
    ↓
[STEP 1] Preprocessing       → Parse, split, resolve triplets
    ↓
[STEP 2] Decision Detection  → Identify decision-related sentences
    ↓
[STEP 3] Metadata Extraction → Extract assignee, deadline
    ↓
[STEP 4] Postprocessing      → Build tasks, score, deduplicate
    ↓
Final Tasks (JSON)
```

## Architecture

### 1️⃣ Preprocessing
Converts raw transcripts into structured, sentence-level data with triplet extraction.

**Input:** Raw transcript (speaker: utterance format)
**Output:** Segmented sentences with S-V-O triplets and confidence scores

**Components:**
- Speaker parsing
- Sentence segmentation (spaCy)
- Text cleaning
- Stopword filtering
- Triplet extraction (resolve pronouns, anaphora, etc.)

**File:** `pipeline/preprocessing/`

### 2️⃣ Decision Detection
Identifies sentences containing actionable decisions using hybrid rule-based + transformer classification.

**Input:** Preprocessed sentences
**Output:** Decision sentences with confidence scores

**Components:**
- Rule-based keyword detection
- Transformer-based zero-shot NLI classification
- Hybrid scoring (combines both approaches)

**Model:** `cross-encoder/nli-distilroberta-base` (250 MB)  
**Threshold:** 0.85

**File:** `pipeline/detection/`

### 3️⃣ Metadata Extraction
Extracts actionable metadata (assignee, deadline) from decisions using QA + NER.

**Input:** Decision sentences
**Output:** Task definitions with metadata

**Components:**
- Assignee extraction (QA model + NER)
- Deadline extraction (temporal expression parsing)

**Model:** `deepset/roberta-base-squad2` (400 MB)  
**File:** `pipeline/extraction/`

### 4️⃣ Postprocessing
Builds final task objects, generates descriptions, scores confidence, and deduplicates.

**Input:** Task definitions
**Output:** Final structured tasks

**Components:**
- Task building & description generation (`google/flan-t5-base` - 990 MB)
- Confidence scoring (weighted fusion of extraction scores)
- Semantic deduplication (embeddings-based cosine similarity)

**Model:** `all-mpnet-base-v2` (420 MB) for deduplication  
**File:** `pipeline/postprocessing/`

## Output Format

#### Final Tasks JSON

```json
[
  {
    "task_id": "task_0",
    "task": "Update the project documentation with the new API specifications.",
    "assignee": "Diana",
    "deadline": null,
    "confidence": 0.87,
    "evidence": {
      "text": "Diana, please update the project documentation with the new API specs.",
      "speaker": "Alice"
    },
    "flags": []
  }
]
```

#### Intermediate Outputs

| Step | Output File | Description |
|------|-------------|-------------|
| 1 | `data/processed/{meeting_id}.json` | Preprocessed sentences |
| 2 | `data/processed/{meeting_id}_decisions.json` | Detected decisions |
| 3 | `data/processed/{meeting_id}_extractions.json` | Extracted metadata |
| 4 | `data/outputs/{meeting_id}_tasks.json` | Final tasks |

## Installation

### Requirements
- Python 3.10+
- CUDA 11.8+ (optional, for GPU acceleration)
- 8+ GB RAM (16+ GB recommended)

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download required models
python -m spacy download en_core_web_sm
```

## Usage

### Command Line

```bash
# Process single meeting
python run_pipeline.py transcripts/meeting.txt

# Process from stdin
python run_pipeline.py < transcripts/meeting.txt

# or
python run_pipeline.py
# (paste transcript, Ctrl+D to end)
```

### Programmatic API

```python
from pipeline import NLPActionExtractor

extractor = NLPActionExtractor()
tasks = extractor.run_pipeline(transcript_text)

for task in tasks:
    print(f"Task: {task['task']}")
    print(f"Assignee: {task['assignee']}")
    print(f"Deadline: {task['deadline']}")
    print(f"Confidence: {task['confidence']:.0%}\n")
```

### Evaluation

```python
from evaluation import Evaluator

evaluator = Evaluator(gold_annotations_dir="data/labeled")

# Evaluate predicted tasks against gold annotations
results = evaluator.evaluate_tasks(predicted_tasks, "meeting1")

print(f"Precision: {results['extraction_metrics']['precision']:.3f}")
print(f"Recall: {results['extraction_metrics']['recall']:.3f}")
print(f"F1-Score: {results['extraction_metrics']['f1']:.3f}")
```

## Project Structure

```
.
├── run_pipeline.py                      # Main entry point
├── requirements.txt                     # Python dependencies
│
├── pipeline/
│   ├── config.py                        # Centralized configuration
│   ├── pipeline.py                      # Orchestrator class
│   ├── preprocessing/                   # STEP 1
│   │   ├── speaker_parsing.py
│   │   ├── sentence_splitting.py
│   │   ├── cleaning.py
│   │   ├── stopword_filtering.py
│   │   └── triplet_resolver.py
│   ├── detection/                       # STEP 2
│   │   └── detector.py
│   ├── extraction/                      # STEP 3
│   │   ├── assignee.py
│   │   └── deadline.py
│   └── postprocessing/                  # STEP 4
│       ├── task_builder.py
│       ├── confidence.py
│       └── deduplication.py
│
├── evaluation/                          # Evaluation framework
│   ├── metrics.py                       # Metrics calculator
│   └── evaluate.py                      # Evaluation runner
│
├── data/
│   ├── raw/                             # Input transcripts
│   ├── processed/                       # Step outputs
│   ├── outputs/                         # Final tasks
│   └── labeled/                         # Gold annotations
│
├── models/                              # Cached model weights
├── transcripts/                         # Sample meetings
├── app/                                 # Flask web interface (optional)
├── documentation/                       # Detailed docs
└── test\ scripts/                       # Testing utilities
```

## Configuration

All settings in `pipeline/config.py`:

```python
# Models
NLI_MODEL = "cross-encoder/nli-distilroberta-base"
QA_MODEL = "deepset/roberta-base-squad2"
SUMMARIZATION_MODEL = "google/flan-t5-base"
EMBEDDING_MODEL = "all-mpnet-base-v2"

# Thresholds
DECISION_THRESHOLD = 0.85
DEDUPLICATION_THRESHOLD = 0.8

# Data directories
DATA_ROOT = "data"
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
OUTPUT_DATA_DIR = "data/outputs"
LABELED_DATA_DIR = "data/labeled"
```

## Documentation

- **[ARCHITECTURE.md](documentation/ARCHITECTURE.md)** - Detailed pipeline architecture and design decisions
- **[data/labeled/README.md](data/labeled/README.md)** - Annotation format for gold-standard evaluation
- **[models/README.md](models/README.md)** - Model management and fine-tuning
- **[evaluation/README.md](evaluation/README.md)** - Evaluation framework documentation (if exists)

## Models & Performance

| Component | Model | Size | Threshold |
|-----------|-------|------|-----------|
| Parsing | spaCy en_core_web_sm | 40 MB | - |
| Decision Detection | cross-encoder/nli-distilroberta-base | 250 MB | 0.85 |
| QA Extraction | deepset/roberta-base-squad2 | 400 MB | 0.50 |
| Description Gen | google/flan-t5-base | 990 MB | - |
| Deduplication | all-mpnet-base-v2 | 420 MB | 0.80 |

**Total:** ~2.1 GB (cached locally)  
**Typical Runtime:** ~17s per meeting (100 sentences)

## Example

### Input
```
Alice: Let's start with the sprint planning for this week.
Bob: I will handle the API refactor by Friday.
Alice: Can you write the integration tests for the new endpoints?
Charlie: I will write the tests by Wednesday.
Diana: Please update the project documentation with the new API specs.
```

### Output
```json
[
  {
    "task_id": "task_0",
    "task": "Start the sprint planning for this week.",
    "assignee": "Alice",
    "deadline": null,
    "confidence": 0.89
  },
  {
    "task_id": "task_1",
    "task": "Handle the API refactor.",
    "assignee": "Bob",
    "deadline": "Friday",
    "confidence": 0.95
  },
  {
    "task_id": "task_2",
    "task": "Write the integration tests for the new endpoints.",
    "assignee": "Alice",
    "deadline": null,
    "confidence": 0.89
  },
  {
    "task_id": "task_3",
    "task": "Write the tests.",
    "assignee": "Charlie",
    "deadline": "Wednesday",
    "confidence": 0.95
  },
  {
    "task_id": "task_4",
    "task": "Update the project documentation with the new API specifications.",
    "assignee": "Diana",
    "deadline": null,
    "confidence": 0.87
  }
]
```

## Development

### Testing

```bash
# Test individual pipeline stages
python test\ scripts/test_decision_detection.py
python test\ scripts/test_task_generation.py
python test\ scripts/test_task_board.py
```

### Evaluation Against Gold Standard

```bash
# Evaluate extraction quality
python -c "from evaluation import Evaluator; e = Evaluator(); print(e.evaluate_all_meetings())"
```

## Troubleshooting

### GPU Memory Issues
- Reduce batch size in config
- Use CPU only: `export CUDA_VISIBLE_DEVICES=""`

### Model Download Issues
```bash
# Set HuggingFace cache location
export HF_HOME=/path/to/large/disk

# Pre-download models
python -c "from transformers import AutoModel; AutoModel.from_pretrained('google/flan-t5-base')"
```

### Missing Confidence Scores
- Check that all extraction steps completed
- Verify input transcript format (Speaker: utterance)

## Future Improvements

- [ ] Multi-lingual support
- [ ] Fine-tuning on domain-specific meetings
- [ ] Coreference resolution
- [ ] Temporal normalization (Friday → 2024-07-12)
- [ ] Dialogue act recognition
- [ ] Interactive refinement UI

## Citation

```bibtex
@misc{meeting_action_extractor,
  title = {Meeting Action Extractor: NLP Pipeline for Task Extraction},
  author = {PDM},
  year = {2024}
}
```

## License

[Add license information]

## References

- Reimers & Gurevych (2019): Sentence-BERT
- de Marneffe et al. (2008): Stanford Dependencies
- Yin et al. (2019): Zero-shot NLI
- Devlin et al. (2019): BERT
- Raffel et al. (2020): FLAN-T5


**Input:** Decision summaries from STEP 4 + transcript from STEP 1
**Output:** Structured tasks with metadata

```json
[
  {"task_id": 0, "title": "Focus on the payment API", "assignee": "B", "deadline": null, "evidence_sentences": [4, 9], "cluster_id": 0}
]
```

**Implementation:** [STEP5_TASK_GENERATION.md](documentation/STEP5_TASK_GENERATION.md)

**Models:** roberta-base-squad2 (QA for assignee) + spaCy en_core_web_sm (NER for deadline)

###  STEP 6: Task Board UI
Interactive web interface for viewing extracted tasks and tracing them to meeting transcript evidence.

**Input:** Tasks from STEP 5 + transcript from STEP 1
**Output:** Web-based task board with evidence traceability

**Features:**
- Task cards with assignee and deadline badges
- Click-to-reveal transcript evidence
- Speaker and sentence-level traceability

**Implementation:** [STEP6_TASK_BOARD.md](documentation/STEP6_TASK_BOARD.md)

**Stack:** FastAPI + Jinja2 + vanilla JavaScript

## Quick Start

### Installation

```bash
# Clone or navigate to project
cd meeting-action-extractor

# Install dependencies
pip install spacy transformers torch sentence-transformers scikit-learn
pip install fastapi uvicorn jinja2 python-multipart

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Single Command Demo

Run the entire pipeline on any transcript with one command:

```bash
python run_pipeline.py transcripts/demo_meeting.txt
```

This will:
1. Load the transcript
2. Run Steps 1–5 (preprocessing → decision detection → clustering → summarization → task generation)
3. Save JSON outputs at every stage
4. Launch the Task Board UI at http://127.0.0.1:8000

You can also paste a transcript from stdin:

```bash
python run_pipeline.py
# Paste transcript, then press CTRL+D
```

### JSON Outputs

Each step saves its results to disk for inspection and reuse:

| Step   | Output File                                       | Description               |
| ------ | ------------------------------------------------- | ------------------------- |
| STEP 1 | `data/processed_transcripts/meeting1.json`        | Sentence-level transcript |
| STEP 2 | `data/decision_sentences/meeting1_decisions.json` | Detected decisions        |
| STEP 3 | `data/decision_clusters/meeting1_clusters.json`   | Clustered decisions       |
| STEP 4 | `data/decision_summaries/meeting1_decisions.json` | Summarized decisions      |
| STEP 5 | `data/tasks/meeting1_tasks.json`                  | Structured tasks          |

### Run Individual Steps

```bash
# STEP 1: Preprocess raw transcript
python example_usage.py

# STEP 2: Detect decisions
python example_decision_detection.py

# STEP 3: Cluster decisions
python -m pipeline.clustering

# STEP 4: Summarize decisions
python example_summarization.py

# STEP 5: Generate tasks
python example_task_generation.py

# STEP 6: Launch task board UI
uvicorn app.main:app --reload
# Open http://127.0.0.1:8000
```

### Results

All scripts process the example meeting in `data/raw_transcripts/meeting1.txt`:

- **STEP 1 Output:** `data/processed_transcripts/meeting1.json` (18 sentences)
- **STEP 2 Output:** `data/decision_sentences/meeting1_decisions.json` (13 decisions)
- **STEP 3 Output:** `data/decision_clusters/meeting1_clusters.json` (5 clusters)
- **STEP 4 Output:** `data/decision_summaries/meeting1_decisions.json` (5 summaries)
- **STEP 5 Output:** `data/tasks/meeting1_tasks.json` (5 tasks)

## Project Structure

```
meeting-action-extractor/
│
├── run_pipeline.py               # ★ Single command demo runner
│
├── transcripts/                  # Input: Transcript files for demo
│   └── demo_meeting.txt
│
├── app/                          # STEP 6: Task Board UI
│   ├── main.py                   # FastAPI backend
│   ├── templates/
│   │   └── index.html            # Task board page
│   └── static/
│       └── script.js             # Frontend logic
│
├── data/
│   ├── raw_transcripts/          # Input: Raw meeting transcripts
│   │   └── meeting1.txt
│   ├── processed_transcripts/    # Output from STEP 1
│   │   └── meeting1.json
│   ├── decision_sentences/       # Output from STEP 2
│   │   └── meeting1_decisions.json
│   ├── decision_clusters/        # Output from STEP 3
│   │   └── meeting1_clusters.json
│   ├── decision_summaries/       # Output from STEP 4
│   │   └── meeting1_decisions.json
│   └── tasks/                    # Output from STEP 5
│       └── meeting1_tasks.json
│
├── pipeline/
│   ├── preprocess.py             # STEP 1 module
│   ├── decision_detector.py      # STEP 2 module
│   ├── clustering.py             # STEP 3 module
│   ├── summarization.py          # STEP 4 module
│   └── task_generator.py         # STEP 5 module
│
├── documentation/
│   ├── PREPROCESSING_STEP1.md
│   ├── DECISION_DETECTION_STEP2.md
│   ├── STEP3_CLUSTERING.md
│   ├── STEP4_SUMMARIZATION.md
│   ├── STEP5_TASK_GENERATION.md
│   └── STEP6_TASK_BOARD.md
│
├── demo scripts/                 # Per-step example scripts
│   ├── example_usage.py          # Run STEP 1
│   ├── example_decision_detection.py # Run STEP 2
│   ├── example_summarization.py  # Run STEP 4
│   └── example_task_generation.py # Run STEP 5
│
├── test scripts/                 # Test suites
│   ├── test_decision_detection.py # STEP 2 tests
│   ├── test_summarization.py     # STEP 4 tests
│   ├── test_task_generation.py   # STEP 5 tests
│   └── test_task_board.py        # STEP 6 tests
│
└── README.md
```

## Technical Details

### STEP 1: Preprocessing

**Technology:**
- spaCy NLP (sentence segmentation)
- Python JSON (serialization)

**Key Features:**
- Extracts speaker and utterance using ":" delimiter
- Segments multi-sentence utterances
- Preserves speaker information
- Handles edge cases (blank lines, extra spaces)

**Output:** Structured list with `sentence_id`, `speaker`, `text`

### STEP 2: Decision Detection

**Technology:**
- Transformers (HuggingFace)
- BART-large-mnli (zero-shot classification)
- PyTorch (neural network backend)

**Key Features:**
- Binary classification: Decision vs Non-Decision
- Zero-shot approach (no fine-tuning)
- Probability threshold filtering
- Preserves all sentence metadata

**Output:** Filtered list with added `decision_probability`

### STEP 3: Decision Clustering

**Technology:**
- SentenceTransformers (all-mpnet-base-v2)
- scikit-learn AgglomerativeClustering
- spaCy (verb-object action analysis)

**Key Features:**
- Semantic + positional + action-object aware similarity
- Precomputed distance matrix
- One cluster per distinct decision

**Output:** Cluster groups with sentence IDs, texts, speakers

### STEP 4: Decision Summarization

**Technology:**
- Transformers (distilbart-cnn-12-6, abstractive summarization)
- Rule-based conversational phrase cleaning
- Pronoun resolution and proper noun capitalization

**Key Features:**
- Hybrid approach: model + rule-based cleaning
- Quality gate rejects poor model output
- Filler word removal (first, just, actually, etc.)
- Pronoun resolution (it → the system)
- Day/month capitalization

**Output:** Concise action-oriented decision statements

### STEP 5: Task Generation

**Technology:**
- Transformers (deepset/roberta-base-squad2, extractive QA)
- spaCy NER (en_core_web_sm, DATE/TIME entity detection)
- Regex fallback for deadline detection

**Key Features:**
- QA-based assignee extraction from evidence context
- NER-based deadline detection
- Graceful fallback to speaker-based assignee and regex deadlines
- Preserves evidence sentence IDs and cluster links
- 1:1 mapping from summaries to tasks

**Output:** Structured task objects with assignee, deadline, evidence

### STEP 6: Task Board UI

**Technology:**
- FastAPI (web framework)
- Jinja2 (HTML templating)
- Vanilla JavaScript (frontend logic)

**Key Features:**
- Task cards with assignee and deadline badges
- Click-to-reveal transcript evidence
- Lazy evidence loading (fetched on demand)
- O(1) sentence lookup via pre-built index
- Read-only (never modifies pipeline outputs)

**Output:** Interactive web-based task board at http://127.0.0.1:8000

## Example Walkthrough

### Input

Raw meeting transcript:
```
A: good morning everyone. let's start with the Q1 planning
B: thanks for having us. I think we should focus on the payment API first
A: absolutely. we need to deploy it by end of march. can you prepare the technical spec?
...
```

### After STEP 1 (18 sentences)

```json
[
  {"sentence_id": 1, "speaker": "A", "text": "good morning everyone."},
  {"sentence_id": 2, "speaker": "A", "text": "let's start with the Q1 planning"},
  {"sentence_id": 3, "speaker": "B", "text": "thanks for having us."},
  {"sentence_id": 4, "speaker": "B", "text": "I think we should focus on the payment API first"},
  ...
]
```

### After STEP 2 (13 decisions)

```json
[
  {"sentence_id": 2, "speaker": "A", "text": "let's start with the Q1 planning", "decision_probability": 0.90},
  {"sentence_id": 4, "speaker": "B", "text": "I think we should focus on the payment API first", "decision_probability": 0.96},
  {"sentence_id": 6, "speaker": "A", "text": "we need to deploy it by end of march.", "decision_probability": 0.96},
  ...
]
```

## Usage Examples

### Process a New Meeting

```python
from pipeline.preprocess import preprocess_transcript, save_processed_transcript

# 1. Load and preprocess
transcript = open("data/raw_transcripts/meeting2.txt").read()
sentences = preprocess_transcript(transcript)
save_processed_transcript(sentences, "data/processed_transcripts/meeting2.json")

# 2. Detect decisions
from pipeline.decision_detector import detect_decisions_in_transcript
decisions = detect_decisions_in_transcript(
    "data/processed_transcripts/meeting2.json",
    "data/decision_sentences/meeting2_decisions.json"
)

# 3. Cluster decisions (run pipeline/clustering.py or use its API)

# 4. Summarize decisions
from pipeline.summarization import summarize_decisions_in_transcript
summaries = summarize_decisions_in_transcript(
    "data/decision_clusters/meeting2_clusters.json",
    "data/decision_summaries/meeting2_decisions.json"
)

for s in summaries:
    print(f"Decision: {s['summary']}")

# 5. Generate tasks
from pipeline.task_generator import generate_tasks_from_transcript
tasks = generate_tasks_from_transcript(
    "data/decision_summaries/meeting2_decisions.json",
    "data/processed_transcripts/meeting2.json",
    "data/tasks/meeting2_tasks.json"
)

for t in tasks:
    print(f"Task: {t['title']} → {t['assignee']} (deadline: {t['deadline']})")
```

### Custom Decision Threshold

```python
from pipeline.decision_detector import DecisionDetector

detector = DecisionDetector(threshold=0.75)  # More strict filtering

decisions = detector.detect_decisions(sentences)
```

### Filter by Speaker

```python
# Get decisions only from specific speaker
alice_decisions = [d for d in decisions if d['speaker'] == 'A']
```

## Pipeline Status

All 6 steps are implemented and operational:

-  STEP 1: Preprocessing
-  STEP 2: Decision Detection
-  STEP 3: Decision Clustering
-  STEP 4: Decision Summarization
-  STEP 5: Task Generation
-  STEP 6: Task Board UI

## Limitations & Design Choices

### STEP 1: Preprocessing
-  Handles multi-sentence utterances
-  Preserves speaker information
-  No NER (named entity recognition)
-  No timestamp extraction (can be added)

### STEP 2: Decision Detection
-  Uses transformer semantics (not rules)
-  Zero-shot (no training required)
-  Handles suggestion/decision ambiguity
-  No context beyond single sentence
-  No fine-tuning (can improve with labeled data)

## Performance

### STEP 1 (Preprocessing)
- **Input:** 573 characters (example meeting)
- **Output:** 18 sentences
- **Time:** <1 second
- **Scalability:** Linear with text length

### STEP 2 (Decision Detection)
- **Input:** 18 sentences
- **Output:** 13 decisions (72% detection rate)
- **Time:** ~50 seconds (includes model download on first run)
- **Subsequent runs:** ~10 seconds
- **Scalability:** Linear with sentence count

## Dependencies

```
spacy                  # Sentence segmentation
transformers          # Transformer models
torch                 # Neural network backend
scikit-learn          # ML utilities (for STEP 3+)
fastapi               # Web framework (STEP 6)
uvicorn               # ASGI server (STEP 6)
jinja2                # HTML templating (STEP 6)
```

Install all:
```bash
pip install spacy transformers torch scikit-learn fastapi uvicorn jinja2
python -m spacy download en_core_web_sm
```

## Output Data Format

### Preprocessed Sentences (STEP 1)
```json
{
  "sentence_id": 1,
  "speaker": "Alice",
  "text": "let's deploy tomorrow"
}
```

### Decision Sentences (STEP 2)
```json
{
  "sentence_id": 1,
  "speaker": "Alice",
  "text": "let's deploy tomorrow",
  "decision_probability": 0.92
}
```

### Expected Clustering Output (STEP 3)
```json
{
  "cluster_id": 0,
  "sentences": [4, 9],
  "texts": ["focus on the payment API", "finalize the pricing model"],
  "speakers": ["B", "B"]
}
```

### Decision Summaries (STEP 4)
```json
{
  "cluster_id": 0,
  "summary": "Focus on the payment API.",
  "evidence_sentences": [4, 9]
}
```

### Tasks (STEP 5)
```json
{
  "task_id": 0,
  "title": "Focus on the payment API",
  "assignee": "B",
  "deadline": null,
  "evidence_sentences": [4, 9],
  "cluster_id": 0
}
```

## Contributing

To extend the pipeline:

1. Add new steps in `pipeline/` directory
2. Follow the same input/output format conventions
3. Preserve metadata through the pipeline
4. Document with examples in README

## References

- **Preprocessing:** spaCy NLP library
- **Decision Detection:** [Zero-shot classifiers with NLI](https://huggingface.co/facebook/bart-large-mnli)
- **Clustering:** [SentenceTransformers](https://www.sbert.net/) + scikit-learn AgglomerativeClustering
- **Summarization:** [DistilBART](https://huggingface.co/sshleifer/distilbart-cnn-12-6) + rule-based post-processing
- **Task Generation:** [RoBERTa QA](https://huggingface.co/deepset/roberta-base-squad2) + [spaCy NER](https://spacy.io/models/en)
- **Task Board:** [FastAPI](https://fastapi.tiangolo.com/) + [Jinja2](https://jinja.palletsprojects.com/)
- **Decision Detection Paper:** Research on decision-related dialogue acts in meetings

## License

(Add your license here)


