"""Transformer-based decision classifier using NLI models."""

import os
from typing import List, Dict

# Apple Silicon safety
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MODEL_NAME = "cross-encoder/nli-distilroberta-base"
DECISION_THRESHOLD = 0.85

CLASSIFICATION_LABELS = [
    "a decision made in the meeting",
    "a person committing to do a future action",
    "general discussion or opinion",
]

LABEL_TO_TYPE = {
    "a decision made in the meeting": "decision",
    "a person committing to do a future action": "commitment",
    "general discussion or opinion": "discussion",
}

KEEP_TYPES = {"decision", "commitment"}

_SHARED_CLASSIFIER_MODEL = None
_SHARED_CLASSIFIER_TOKENIZER = None
_SHARED_CLASSIFIER_DEVICE = None
_SHARED_CLASSIFIER_ENTAILMENT_IDX = None


class TransformerClassifier:
    """
    Transformer-based classifier for decision detection using NLI.
    
    Uses pretrained NLI model for zero-shot classification.
    Decision/Commitment → keep, Discussion → discard.
    """
    
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        threshold: float = DECISION_THRESHOLD,
        batch_size: int = 1,
    ):
        """
        Initialize transformer classifier.
        
        Args:
            model_name (str): HuggingFace model identifier
            threshold (float): Confidence threshold for decisions (0-1)
            batch_size (int): Batch size for inference
        """
        self.model_name = model_name
        self.threshold = threshold
        self.batch_size = batch_size
        self._model = None
        self._tokenizer = None
        self._device = None
        self.device_type = "cpu"
    
    def _ensure_loaded(self):
        """Lazy-load model on first use."""
        global _SHARED_CLASSIFIER_MODEL, _SHARED_CLASSIFIER_TOKENIZER
        global _SHARED_CLASSIFIER_DEVICE, _SHARED_CLASSIFIER_ENTAILMENT_IDX

        if self._model is not None:
            return
        
        try:
            if (
                _SHARED_CLASSIFIER_MODEL is None
                or _SHARED_CLASSIFIER_TOKENIZER is None
                or _SHARED_CLASSIFIER_DEVICE is None
                or _SHARED_CLASSIFIER_ENTAILMENT_IDX is None
            ):
                print("[*] Loading zero-shot classification model...")
                import torch
                from transformers import AutoTokenizer, AutoModelForSequenceClassification

                torch.set_num_threads(1)
                _SHARED_CLASSIFIER_DEVICE = torch.device("cpu")

                _SHARED_CLASSIFIER_TOKENIZER = AutoTokenizer.from_pretrained(self.model_name)
                _SHARED_CLASSIFIER_MODEL = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    dtype=torch.float32,
                    low_cpu_mem_usage=False,
                )
                _SHARED_CLASSIFIER_MODEL.to(_SHARED_CLASSIFIER_DEVICE)
                _SHARED_CLASSIFIER_MODEL.eval()

                id2label = _SHARED_CLASSIFIER_MODEL.config.id2label
                entailment_idx = None
                for idx, label in id2label.items():
                    if label.lower() == "entailment":
                        entailment_idx = int(idx)
                        break
                if entailment_idx is None:
                    entailment_idx = len(id2label) - 1
                _SHARED_CLASSIFIER_ENTAILMENT_IDX = entailment_idx

            self._tokenizer = _SHARED_CLASSIFIER_TOKENIZER
            self._model = _SHARED_CLASSIFIER_MODEL
            self._device = _SHARED_CLASSIFIER_DEVICE
            self._entailment_idx = _SHARED_CLASSIFIER_ENTAILMENT_IDX
            
            print(f"[+] Classifier loaded: {self.model_name}")
        except Exception as e:
            raise OSError(f"Failed to load classifier: {str(e)}")
    
    def predict_sentence(self, sentence: str) -> Dict:
        """
        Predict semantic category for a sentence.
        
        Returns dict with keys:
        - predicted_label (str)
        - decision_type (str): 'decision', 'commitment', or 'discussion'
        - confidence_score (float)
        """
        self._ensure_loaded()
        
        try:
            import torch
            
            hypotheses = [f"This text is {label}." for label in CLASSIFICATION_LABELS]
            scores = []
            
            for h in hypotheses:
                inputs = self._tokenizer(
                    sentence,
                    h,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    logits = self._model(**inputs).logits
                    probs = torch.softmax(logits, dim=-1)
                    scores.append(probs[0, self._entailment_idx].item())
            
            total = sum(scores)
            scores = [s / total for s in scores] if total > 0 else scores
            
            best_idx = scores.index(max(scores))
            best_label = CLASSIFICATION_LABELS[best_idx]
            
            return {
                "predicted_label": best_label,
                "decision_type": LABEL_TO_TYPE[best_label],
                "confidence_score": scores[best_idx],
            }
        except Exception as e:
            return {
                "predicted_label": CLASSIFICATION_LABELS[2],
                "decision_type": "discussion",
                "confidence_score": 0.0,
            }
    
    def predict_batch(self, sentences: List[str]) -> List[Dict]:
        """Classify batch of sentences."""
        return [self.predict_sentence(s) for s in sentences]
