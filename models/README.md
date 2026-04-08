# Cached Models

This directory stores pre-downloaded and fine-tuned models used by the pipeline.

## Models

### 1. Sentence Splitter: `en_core_web_sm`
- **Location**: Downloaded via spaCy
- **Size**: ~40 MB
- **Purpose**: Dependency parsing for sentence splitting and triplet extraction

### 2. Decision Detection: `cross-encoder/nli-distilroberta-base`
- **Location**: Downloaded from HuggingFace Hub
- **Size**: ~250 MB
- **Purpose**: Zero-shot classification for decision detection
- **Threshold**: 0.5 (tunable)

### 3. Metadata Extraction: `deepset/roberta-base-squad2`
- **Location**: Downloaded from HuggingFace Hub
- **Size**: ~400 MB
- **Purpose**: Question-answering for extracting assignee and deadline
- **Models**:
  - Assignee QA model
  - Deadline QA model

### 4. Task Description: `google/flan-t5-base`
- **Location**: Downloaded from HuggingFace Hub
- **Size**: ~990 MB
- **Purpose**: Generating task descriptions from extracted metadata

### 5. Semantic Similarity: `sentence-transformers/all-mpnet-base-v2`
- **Location**: Downloaded via sentence-transformers
- **Size**: ~420 MB
- **Purpose**: Computing semantic embeddings for deduplication
- **Fine-tuning**: Optional on meeting transcripts

## Caching Strategy

Models are automatically downloaded on first use and cached by the libraries:
- **spaCy models**: `~/.cache/spacy/models/`
- **HuggingFace models**: `~/.cache/huggingface/hub/`
- **Sentence Transformers**: `~/.cache/sentence_transformers/`

To use custom cache locations, set environment variables:
```bash
export TORCH_HOME=/path/to/models/
export TRANSFORMERS_CACHE=/path/to/models/
export HF_HOME=/path/to/models/
```

## Fine-tuning

For improved performance on domain-specific meetings, models can be fine-tuned:

1. **Decision Detection Fine-tuning**: Use `data/labeled/` with gold annotations
2. **Metadata Extraction Fine-tuning**: Create QA pairs from meeting transcripts
3. **Task Generation Fine-tuning**: Collect human-annotated descriptions

See documentation for fine-tuning procedures.

## Memory Requirements

- **Minimum**: 8 GB RAM (single model at inference time)
- **Recommended**: 16 GB RAM (multiple models loaded)
- **Batch Inference**: 24+ GB RAM for large batch processing

## Model Updating

To use newer versions of models, update `pipeline/config.py`:

```python
MODEL_NAMES = {
    "sentence_splitter": "en_core_web_sm",  # spaCy model
    "decision_detector": "cross-encoder/nli-distilroberta-base",
    "qa_extractor": "deepset/roberta-base-squad2",
    "description_gen": "google/flan-t5-base",
    "embedder": "sentence-transformers/all-mpnet-base-v2",
}
```

Then delete the cached models to force downloading the new versions.
