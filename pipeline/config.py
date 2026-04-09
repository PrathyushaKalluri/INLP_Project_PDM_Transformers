"""Pipeline configuration."""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Enabled features
USE_TRANSFORMER_CLASSIFIER = True
USE_RULE_BASED_DETECTION = True

# Model names
NLI_MODEL = "cross-encoder/nli-distilroberta-base"
QA_MODEL = "deepset/roberta-base-squad2"
SUMMARIZATION_MODEL = "google/flan-t5-base"
EMBEDDING_MODEL = "all-mpnet-base-v2"

# Thresholds
DECISION_THRESHOLD = 0.85
DEDUPLICATION_THRESHOLD = 0.8
DEDUPLICATION_SIMILARITY = 0.8

# Clustering
DISTANCE_THRESHOLD = 0.70
POSITION_DECAY = 0.05
MIN_SIMILARITY = 0.40

# Data paths
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_ROOT / "raw"
PROCESSED_DATA_DIR = DATA_ROOT / "processed"
OUTPUT_DATA_DIR = DATA_ROOT / "outputs"
LABELED_DATA_DIR = DATA_ROOT / "labeled"

# Ensure directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DATA_DIR, LABELED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
