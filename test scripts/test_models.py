"""
Pre-download and verify all ML models used in the pipeline.

Models:
  - deepset/roberta-base-squad2         (~500MB) — STEP 5: QA for assignee
  - sshleifer/distilbart-cnn-12-6       (~1.2GB) — STEP 4: Summarization
  - all-mpnet-base-v2                   (~420MB) — STEP 3: Sentence embeddings
  - en_core_web_sm                      (~12MB)  — STEP 5: NER for deadline
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("=" * 60)
print("PRE-DOWNLOADING ML MODELS")
print("=" * 60)

# 1. QA model (STEP 5)
print("\n[1/4] Loading QA model: deepset/roberta-base-squad2...")
from transformers import pipeline as hf_pipeline
qa = hf_pipeline("question-answering", model="deepset/roberta-base-squad2")
print("  ✓ QA model loaded")

# 2. Summarization model (STEP 4)
print("\n[2/4] Loading summarization model: sshleifer/distilbart-cnn-12-6...")
summarizer = hf_pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
print("  ✓ Summarization model loaded")

# 3. Sentence embeddings (STEP 3)
print("\n[3/4] Loading sentence embedding model: all-mpnet-base-v2...")
from sentence_transformers import SentenceTransformer
emb = SentenceTransformer("all-mpnet-base-v2")
print("  ✓ Sentence embedding model loaded")

# 4. spaCy NER (STEP 5)
print("\n[4/4] Loading spaCy model: en_core_web_sm...")
import spacy
nlp = spacy.load("en_core_web_sm")
print("  ✓ spaCy NER model loaded")

print("\n" + "=" * 60)
print("ALL MODELS LOADED SUCCESSFULLY")
print("=" * 60)
