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
        if self._model is not None:
            return
        
        try:
            print("[*] Loading zero-shot classification model...")
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            torch.set_num_threads(1)
            self._device = torch.device("cpu")
            
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                dtype=torch.float32,
                low_cpu_mem_usage=False,
            )
            self._model.to(self._device)
            self._model.eval()
            
            # Detect entailment index
            id2label = self._model.config.id2label
            self._entailment_idx = None
            for idx, label in id2label.items():
                if label.lower() == "entailment":
                    self._entailment_idx = int(idx)
                    break
            if self._entailment_idx is None:
                self._entailment_idx = len(id2label) - 1
            
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
