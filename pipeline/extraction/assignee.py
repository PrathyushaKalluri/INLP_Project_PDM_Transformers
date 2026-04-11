"""Extract assignee (responsible person) from task context."""

import os
import re
from typing import List, Dict, Optional, Set

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

QA_MODEL_NAME = "deepset/roberta-base-squad2"
QA_QUESTION = "Who will do this?"

# Common generic speaker names and aliases
GENERIC_SPEAKERS = {"speaker1", "speaker2", "person1", "person2", "participant"}

_SHARED_QA_MODEL = None
_SHARED_QA_TOKENIZER = None
_SHARED_QA_DEVICE = None


class AssigneeExtractor:
    """
    Extract assignee (responsible person) from evidence sentences.
    
    Uses rule-based extraction first (faster, more reliable), then falls back to QA model only if needed.
    
    Priority:
    1. Self-commitment (subject is "I") → speaker is assignee
    2. Named addressee ("Charlie, can you...") → named person
    3. Team commitment (subject is "We" or "team") → "team"
    4. QA model fallback (expensive, less reliable)
    5. Default to speaker
    """
    
    def __init__(self, qa_model_name: str = QA_MODEL_NAME):
        """Initialize assignee extractor."""
        self.qa_model_name = qa_model_name
        self._qa_model = None
        self._qa_tokenizer = None
        self._device = None
        self.use_qa = False
        self._known_speakers: Set[str] = set()  # Will be populated dynamically
    
    def set_known_speakers(self, speakers: Set[str]):
        """
        Set known speakers for this extraction context.
        
        Args:
            speakers (Set[str]): Set of known speaker names
        """
        self._known_speakers = speakers
    
    def _ensure_loaded(self):
        """Lazy-load QA model."""
        global _SHARED_QA_MODEL, _SHARED_QA_TOKENIZER, _SHARED_QA_DEVICE

        if self._qa_model is not None:
            return
        
        try:
            if _SHARED_QA_MODEL is None or _SHARED_QA_TOKENIZER is None or _SHARED_QA_DEVICE is None:
                print(f"[*] Loading QA model: {self.qa_model_name}")
                import torch
                from transformers import AutoTokenizer, AutoModelForQuestionAnswering

                torch.set_num_threads(1)
                _SHARED_QA_DEVICE = torch.device("cpu")
                self._torch = torch

                _SHARED_QA_TOKENIZER = AutoTokenizer.from_pretrained(self.qa_model_name)
                _SHARED_QA_MODEL = AutoModelForQuestionAnswering.from_pretrained(
                    self.qa_model_name,
                    dtype=torch.float32,
                    low_cpu_mem_usage=False,
                )
                _SHARED_QA_MODEL.to(_SHARED_QA_DEVICE)
                _SHARED_QA_MODEL.eval()

            self._qa_tokenizer = _SHARED_QA_TOKENIZER
            self._qa_model = _SHARED_QA_MODEL
            self._device = _SHARED_QA_DEVICE
            self.use_qa = True
            print(f"[+] QA model loaded")
        except Exception as e:
            print(f"[!] Warning: Could not load QA model: {e}")
            print(f"[!] Falling back to speaker-based extraction")
    
    def _extract_by_rule(self, evidence_sentences: List[Dict]) -> Optional[str]:
        """
        Extract assignee using rule-based patterns.
        
        Returns None if no rule matches (then QA model will be tried).
        """
        if not evidence_sentences:
            return None
        
        sent = evidence_sentences[0]
        text = sent.get("text", "").lower()
        speaker = sent.get("speaker", "")
        subject = sent.get("subject", "").lower() if sent.get("subject") else ""
        
        # Rule 1: Self-commitment (subject is "I" or "me")
        # "I will deploy the API" → speaker is assignee
        if subject in {"i", "me"}:
            return speaker
        
        # Rule 2: Named addressee in imperatives or direct address
        # "Charlie, can you deploy?" → "Charlie"
        # Pattern: First token before comma or first proper noun
        first_tokens = text.split()[:3]  # Check first few tokens
        for token in first_tokens:
            clean_token = token.rstrip(",:").strip()
            # Check if it's a known speaker (case-insensitive)
            if clean_token in self._known_speakers or clean_token.capitalize() in self._known_speakers:
                return clean_token.capitalize()
        
        # Rule 3: Team commitment (subject is "we" or "team")
        # "We should finalize pricing" → team responsibility
        if subject in {"we", "team", "everyone", "all"}:
            return "team"
        
        # Rule 4: Direct references to specific people
        # "The front-end team should review"
        for speaker_name in self._known_speakers:
            pattern = r"\b" + re.escape(speaker_name) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                return speaker_name
        
        # No rule matched
        return None
    
    def extract(self, evidence_sentences: List[Dict]) -> Optional[str]:
        """
        Extract assignee from evidence sentences.
        
        Args:
            evidence_sentences (List[Dict]): List of sentence dicts with speaker/text/subject
        
        Returns:
            str: Assignee name, "team", or speaker name
        """
        if not evidence_sentences:
            return None
        
        first_speaker = evidence_sentences[0].get("speaker")
        
        # Try rule-based extraction first (fast, reliable)
        rule_result = self._extract_by_rule(evidence_sentences)
        if rule_result:
            return rule_result
        
        # Only use QA model if rules didn't match
        self._ensure_loaded()
        
        if not self.use_qa:
            return first_speaker
        
        try:
            # Build context from all evidence sentences
            context_parts = []
            for sent in evidence_sentences:
                context_parts.append(sent.get("text", ""))
            context = " ".join(context_parts)
            
            # Run QA model with cleaner question
            inputs = self._qa_tokenizer(
                QA_QUESTION,
                context,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            with self._torch.no_grad():
                outputs = self._qa_model(**inputs)
                start_idx = self._torch.argmax(outputs.start_logits, dim=-1).item()
                end_idx = self._torch.argmax(outputs.end_logits, dim=-1).item()
            
            # Extract and clean answer
            answer_tokens = inputs["input_ids"][0, start_idx:end_idx+1]
            answer = self._qa_tokenizer.decode(answer_tokens, skip_special_tokens=True)
            
            # Clean up answer
            answer = answer.strip()
            if len(answer) > 1 and answer not in GENERIC_SPEAKERS:
                return answer
            
            # If QA fails or returns garbage, use speaker
            return first_speaker
        except Exception as e:
            print(f"[!] QA extraction failed: {e}")
            return first_speaker

