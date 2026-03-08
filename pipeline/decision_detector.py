"""
Decision Detection Module (STEP 2)

Identifies decision-related dialogue acts (decisions, commitments, concrete next actions)
from meeting transcripts using transformer-based sentence classification.

Methodology:
- Uses pretrained NLI model for multi-label zero-shot classification
- Loads model manually (AutoTokenizer + AutoModelForSequenceClassification)
  to avoid HuggingFace pipeline(device=-1) bus errors on Apple Silicon
- Classifies each sentence into three semantic categories:
    1. Decision — explicit decisions made in the meeting
    2. Commitment — a person committing to a future action
    3. Discussion — general discussion, opinions, or backchannel responses
- Merges Decision + Commitment → decision candidates; discards Discussion
- Applies probability threshold to filter candidates
- Preserves metadata for evidence linking and clustering

Apple Silicon (M1/M2/M3) compatibility:
- Forces CPU device with torch.float32 for stability
- Disables tokenizer parallelism (prevents deadlocks)
- Enables PYTORCH_ENABLE_MPS_FALLBACK as safety net
- Limits CPU threads via torch.set_num_threads(1) to prevent bus errors
- Uses low_cpu_mem_usage=False for safe weight loading
- Uses batch_size=1 inference with torch.no_grad()

Limitations acknowledged:
1. Suggestions vs Decisions - ambiguous phrases included as candidates
2. Backchannel responses - must be learned by model, not filtered by rules
3. Multi-sentence decisions - handled at sentence level (STEP 1 does segmentation)
4. Context dependency - sentences lack surrounding context
5. Class imbalance - most sentences are not decisions (mitigated by threshold)
"""

import json
import os
from pathlib import Path
from typing import List, Dict

# ── Apple Silicon safety: set BEFORE importing torch/transformers ───────
# Prevents MPS (Metal Performance Shaders) from crashing on unsupported ops
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
# Prevents deadlocks when tokenizer uses multiprocessing internally
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Suppress noisy warnings
os.environ["TORCH_COMPILE_DEBUG"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Configuration
DECISION_THRESHOLD = 0.85
BATCH_SIZE = 1  # batch_size=1 is safest for memory on 8GB machines

# Multi-label classification labels — descriptive phrases guide the NLI model
CLASSIFICATION_LABELS = [
    "a decision made in the meeting",
    "a person committing to do a future action",
    "general discussion or opinion",
]

# Map NLI labels back to short decision type strings
LABEL_TO_TYPE = {
    "a decision made in the meeting": "decision",
    "a person committing to do a future action": "commitment",
    "general discussion or opinion": "discussion",
}

# Only decision and commitment types are kept as candidates
KEEP_TYPES = {"decision", "commitment"}

# Lightweight NLI model (~330MB) — works reliably on 8GB Apple Silicon
# (facebook/bart-large-mnli is ~1.6GB and causes bus errors on low-RAM Macs)
MODEL_NAME = "cross-encoder/nli-distilroberta-base"

# ── Post-classification filter ──────────────────────────────────────────
# These patterns catch non-actionable sentences that NLI may still score
# highly as "commitments" (e.g. greetings, facilitation, meta-discussion).
# Applied AFTER NLI scoring to avoid masking model behaviour.

import re as _re

# Sentences matching these patterns are discarded even if NLI says "decision"
NON_ACTION_PATTERNS = [
    # Greetings and pleasantries
    _re.compile(r"^\s*good\s+(morning|afternoon|evening|day)\b", _re.I),
    _re.compile(r"^\s*(hi|hello|hey|welcome)\b", _re.I),
    _re.compile(r"^\s*thanks?\s+(for|everyone|all)\b", _re.I),
    # Short confirmations / acknowledgements (≤6 words)
    _re.compile(
        r"^\s*(sure|perfect|great|sounds?\s+good|agreed|absolutely|no\s+problem"
        r"|will\s+do|okay|ok|fine|right|exactly|definitely|no\s+blame\s+here)\s*\.?\s*$",
        _re.I,
    ),
    # Meeting facilitation / scheduling — "let's start", "let's begin",
    # "let's meet", "let's schedule a follow-up"
    _re.compile(
        r"^\s*let'?s\s+(start|begin|get\s+started|move\s+on|kick\s+off"
        r"|meet\s+again|schedule\s+(a\s+)?follow|wrap\s+up)\b",
        _re.I,
    ),
    # Pure observations with no action verb: "The endpoints are too slow"
    _re.compile(r"^\s*the\s+\w+\s+(is|are|was|were)\s+(too|very|really)\b", _re.I),
]

# Minimum word count — ultra-short utterances are rarely real tasks
MIN_DECISION_WORDS = 4


def _is_non_actionable(text: str) -> bool:
    """Return True if a sentence is a greeting, acknowledgement, or meta-discussion."""
    stripped = text.strip().rstrip(".!?")
    # Check word count
    if len(stripped.split()) < MIN_DECISION_WORDS:
        return True
    # Check patterns
    for pattern in NON_ACTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


class DecisionDetector:
    """
    Transformer-based classifier for identifying decision-related sentences.

    Uses pretrained NLI model for zero-shot classification.
    Decision / Commitment → keep, Discussion → discard.

    Loads model manually via AutoTokenizer + AutoModelForSequenceClassification
    instead of the HuggingFace pipeline() wrapper to avoid bus errors on
    Apple Silicon (Mac M1/M2/M3) with PyTorch 2.x.
    """

    def __init__(self, threshold: float = DECISION_THRESHOLD, batch_size: int = BATCH_SIZE):
        """
        Initialize decision detector with transformer model.

        Args:
            threshold (float): Probability threshold for decision classification (0-1)
            batch_size (int): Number of sentences to classify in each batch

        Raises:
            OSError: If model cannot be loaded
        """
        self.threshold = threshold
        self.batch_size = batch_size

        try:
            print("[*] Loading zero-shot classification model...")
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            self.torch = torch

            # Limit CPU threads to 1 — prevents bus errors on Apple Silicon
            # where multi-threaded BLAS/MKL operations can crash
            torch.set_num_threads(1)

            # Force CPU — MPS can cause bus errors with NLI models
            self.device = torch.device("cpu")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

            # Load model with Apple Silicon safe settings:
            # - torch_dtype=torch.float32: float16 can be unstable on CPU
            # - low_cpu_mem_usage=False: safer weight loading (avoids partial-load crashes)
            # - .to(device): explicit CPU placement
            self.model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_NAME,
                dtype=torch.float32,
                low_cpu_mem_usage=False,
            )
            self.model.to(self.device)
            self.model.eval()

            # Detect NLI label ordering from model config
            # Different NLI models use different index→label mappings
            id2label = self.model.config.id2label
            self._entailment_idx = None
            for idx, label in id2label.items():
                if label.lower() == "entailment":
                    self._entailment_idx = int(idx)
                    break
            if self._entailment_idx is None:
                # Fallback: last index (BART-mnli convention)
                self._entailment_idx = len(id2label) - 1

            print(f"[✓] Classifier loaded successfully")
            print(f"    Model:      {MODEL_NAME}")
            print(f"    Device:     cpu")
            print(f"    Dtype:      float32")
            print(f"    Entailment: index {self._entailment_idx}")
        except Exception as e:
            raise OSError(f"Failed to load classifier: {str(e)}")

    def _run_nli(self, premise: str, hypothesis: str) -> float:
        """
        Run NLI inference for one premise–hypothesis pair.

        Returns the entailment probability.

        Args:
            premise (str): The sentence to classify
            hypothesis (str): NLI hypothesis string

        Returns:
            float: Entailment probability (0-1)
        """
        # Tokenize with explicit truncation to avoid OOM on long sentences
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        # Move tensors explicitly to CPU
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # torch.no_grad() reduces memory by skipping gradient computation
        with self.torch.no_grad():
            logits = self.model(**inputs).logits
            probs = self.torch.softmax(logits, dim=-1)
            return probs[0, self._entailment_idx].item()

    def predict_sentence(self, sentence: str) -> Dict:
        """
        Predict the semantic category and confidence for a sentence.

        Runs NLI entailment against each classification label hypothesis,
        normalizes the scores, and returns the best-matching category.

        Args:
            sentence (str): Input sentence text

        Returns:
            dict: Classification result with keys:
                  - predicted_label (str): winning NLI label
                  - decision_type (str): one of 'decision', 'commitment', 'discussion'
                  - confidence_score (float): probability of the winning label (0-1)
        """
        try:
            # Build hypotheses from labels
            hypotheses = [f"This text is {label}." for label in CLASSIFICATION_LABELS]

            # Get entailment score for each hypothesis (batch_size=1 per hypothesis)
            scores = [self._run_nli(sentence, h) for h in hypotheses]

            # Normalize scores to sum to 1
            total = sum(scores)
            if total > 0:
                scores = [s / total for s in scores]

            # Find best label
            best_idx = scores.index(max(scores))
            best_label = CLASSIFICATION_LABELS[best_idx]
            best_score = scores[best_idx]

            return {
                "predicted_label": best_label,
                "decision_type": LABEL_TO_TYPE[best_label],
                "confidence_score": best_score,
            }
        except Exception as e:
            print(f"[!] Error classifying sentence: {e}")
            return {
                "predicted_label": "general discussion or opinion",
                "decision_type": "discussion",
                "confidence_score": 0.0,
            }

    def predict_batch(self, sentences: List[str]) -> List[Dict]:
        """
        Classify a batch of sentences (sequential processing for memory safety).

        Args:
            sentences (list[str]): Batch of sentence texts

        Returns:
            list[dict]: Per-sentence classification results
        """
        return [self.predict_sentence(s) for s in sentences]

    # ── Legacy single-sentence API (backward compatibility) ─────────────
    def predict_decision(self, sentence: str) -> float:
        """
        Predict probability that a sentence expresses a decision.

        Args:
            sentence (str): Input sentence text

        Returns:
            float: Decision probability (0-1)
                   > 0.75 = likely decision or commitment
                   <= 0.75 = likely discussion

        Note:
            Legacy convenience wrapper around predict_sentence().
            Kept for backward compatibility with external callers.
        """
        prediction = self.predict_sentence(sentence)
        if prediction["decision_type"] in KEEP_TYPES:
            return prediction["confidence_score"]
        return 1.0 - prediction["confidence_score"]

    def detect_decisions(self, sentences: List[Dict]) -> List[Dict]:
        """
        Classify all sentences and filter decision candidates.

        Args:
            sentences (list): Structured sentences from STEP 1 with keys:
                             - sentence_id (int)
                             - speaker (str)
                             - text (str)

        Returns:
            list: Sentences predicted as decisions/commitments with keys:
                  - sentence_id (int)
                  - speaker (str)
                  - text (str)
                  - decision_probability (float)
                  - decision_type (str): 'decision' or 'commitment'

        Algorithm:
        1. Process each sentence sequentially (batch_size=1 for memory safety)
        2. Predict semantic category via NLI entailment
        3. Keep only decision/commitment sentences above threshold
        4. Preserve original metadata
        5. Add decision probability and decision type
        """
        decisions = []
        total = len(sentences)

        print(f"\n[*] Classifying {total} sentences...")
        print(f"[*] Decision threshold: {self.threshold}")
        print(f"[*] Labels: {CLASSIFICATION_LABELS}")

        for idx, sentence in enumerate(sentences):
            prediction = self.predict_sentence(sentence["text"])
            dtype = prediction["decision_type"]
            score = prediction["confidence_score"]

            # Keep decision and commitment sentences above threshold,
            # but reject greetings / facilitation / observations
            if dtype in KEEP_TYPES and score > self.threshold:
                if _is_non_actionable(sentence["text"]):
                    print(f"  [skip] Non-actionable: {sentence['text'][:60]}...")
                    continue
                decision_obj = {
                    **sentence,  # Preserve all original metadata
                    "decision_probability": round(score, 4),
                    "decision_type": dtype,
                }
                decisions.append(decision_obj)

            # Progress indicator every 5 sentences
            if (idx + 1) % max(1, total // 4) == 0 or (idx + 1) == total:
                print(f"  [{idx + 1}/{total}] Processed...")

        print(f"[✓] Classification complete")
        print(f"[✓] Found {len(decisions)} decision candidates")
        print(f"[*] Detection rate: {len(decisions) / total * 100:.1f}%")

        # Breakdown by type
        type_counts = {}
        for d in decisions:
            t = d["decision_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items()):
            print(f"    {t}: {c}")

        return decisions


def load_processed_transcript(input_path: str) -> List[Dict]:
    """
    Load structured sentences from STEP 1 preprocessing output.

    Args:
        input_path (str): Path to JSON file with preprocessed sentences

    Returns:
        list: List of sentence dictionaries
    """
    with open(input_path, "r") as f:
        return json.load(f)


def save_decision_sentences(decisions: List[Dict], output_path: str) -> None:
    """
    Save detected decision sentences to JSON file.

    Args:
        decisions (list): List of decision sentence dictionaries
        output_path (str): Path to output JSON file
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(decisions, f, indent=2)

    print(f"[✓] Decision sentences saved to: {output_path}")


def detect_decisions_in_transcript(
    input_path: str,
    output_path: str,
    threshold: float = DECISION_THRESHOLD,
) -> List[Dict]:
    """
    End-to-end pipeline: load transcript → detect decisions → save output.

    Args:
        input_path (str): Path to preprocessed transcript JSON
        output_path (str): Path to save decision sentences JSON
        threshold (float): Decision probability threshold

    Returns:
        list: Detected decision sentences
    """
    # Load preprocessed sentences
    print(f"\n[*] Loading preprocessed transcript: {input_path}")
    sentences = load_processed_transcript(input_path)
    print(f"[✓] Loaded {len(sentences)} sentences")

    # Initialize detector
    detector = DecisionDetector(threshold=threshold)

    # Detect decisions
    decisions = detector.detect_decisions(sentences)

    # Save output
    save_decision_sentences(decisions, output_path)

    return decisions


if __name__ == "__main__":
    # Example usage
    input_file = "data/processed_transcripts/meeting1.json"
    output_file = "data/decision_sentences/meeting1_decisions.json"

    print("=" * 70)
    print("STEP 2: DECISION DETECTION (Multi-Label)")
    print("=" * 70)

    try:
        decisions = detect_decisions_in_transcript(
            input_path=input_file,
            output_path=output_file,
            threshold=DECISION_THRESHOLD,
        )

        print("\n" + "=" * 70)
        print("DETECTED DECISIONS")
        print("=" * 70)

        for decision in decisions[:5]:
            print(f"\nID: {decision['sentence_id']}")
            print(f"Speaker: {decision['speaker']}")
            print(f"Text: {decision['text']}")
            print(f"Type: {decision['decision_type']}")
            print(f"Confidence: {decision['decision_probability']:.2%}")

        if len(decisions) > 5:
            print(f"\n... and {len(decisions) - 5} more decisions")

        print("\n" + "=" * 70)
        print(f"✓ Step 2 complete: {len(decisions)} decision candidates identified")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("  Make sure STEP 1 (preprocessing) has been run first")
