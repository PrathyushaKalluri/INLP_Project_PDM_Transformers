"""
Task Generation Module (STEP 5)

Converts decision summaries (from STEP 4) into structured task objects
with ML-extracted metadata (assignee, deadline).

Methodology:
1. Load decision summaries from STEP 4
2. Load full transcript sentences from STEP 1 (for speaker/context metadata)
3. For each summary:
   a. Retrieve evidence sentences from transcript
   b. Build context string with speaker labels
   c. Run QA model to extract the responsible person (assignee)
   d. Run NER model to detect deadline expressions (DATE/TIME entities)
   e. Construct structured task object
4. Export tasks as JSON

ML Models Used:
- Question Answering: deepset/roberta-base-squad2 (~500MB)
  Extracts the person responsible for a task from evidence context
- Named Entity Recognition: spaCy en_core_web_sm (~12MB)
  Detects DATE and TIME entities for deadline extraction

Fallback behaviour:
- If QA model is unavailable → use speaker of first evidence sentence
- If NER model is unavailable → use regex-based date pattern matching
- Both fallbacks are deterministic and tested

Apple Silicon (M1/M2/M3) compatibility:
- Manual model loading on CPU device
- Single-threaded torch inference
- All safety settings from previous steps applied
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

# ── Apple Silicon safety: set BEFORE importing torch/transformers ───────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_COMPILE_DEBUG"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ── Configuration ───────────────────────────────────────────────────────
QA_MODEL_NAME = "deepset/roberta-base-squad2"  # Extractive QA (~500MB)
QA_QUESTION = "Who is responsible for performing this task?"

# Regex fallback patterns for deadline detection when spaCy is unavailable
DEADLINE_PATTERNS = [
    # "by end of March", "by next Wednesday", "by Friday", "by tomorrow"
    r"\bby\s+(end\s+of\s+)?(next\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june"
    r"|july|august|september|october|november|december"
    r"|tomorrow|today|tonight|week|month|quarter"
    r"|Q[1-4])\b",
    # "next Wednesday", "next month", "next week"
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|week|month|quarter)\b",
    # "end of March", "end of the month"
    r"\bend\s+of\s+(the\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june"
    r"|july|august|september|october|november|december"
    r"|week|month|quarter)\b",
    # Explicit dates: "March 15", "15 March", "3/15"
    r"\b(january|february|march|april|may|june"
    r"|july|august|september|october|november|december)"
    r"\s+\d{1,2}\b",
    r"\b\d{1,2}\s+(january|february|march|april|may|june"
    r"|july|august|september|october|november|december)\b",
    # ISO-like or slash dates: "2026-03-15", "3/15/2026"
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b",
    # "tomorrow", "today"
    r"\btomorrow\b",
    r"\btoday\b",
]

# ── Deadline validation ─────────────────────────────────────────────────
# spaCy NER tags many things as DATE/TIME that aren't useful deadlines
# (e.g. "morning", "last week", "the task week", "recently").

_INVALID_DEADLINE_PATTERNS = [
    re.compile(r"^\s*(morning|afternoon|evening|night)\s*$", re.I),
    re.compile(r"\b(last|previous|earlier|recently|ago)\b", re.I),
    re.compile(r"^\s*the\s+task\s+week\s*$", re.I),
    re.compile(r"^\s*(now|currently|right now)\s*$", re.I),
]

# Only accept deadlines that contain a recognisable temporal anchor
_VALID_DEADLINE_ANCHORS = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|january|february|march|april|may|june|july|august|september"
    r"|october|november|december"
    r"|tomorrow|today|tonight|end\s+of"
    r"|next\s+week|next\s+month|next\s+quarter"
    r"|Q[1-4]|\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2})\b",
    re.I,
)


def _is_valid_deadline(candidate: str) -> bool:
    """Return True if a NER-extracted deadline is a real, future-oriented date."""
    if not candidate or len(candidate.strip()) < 3:
        return False
    for pat in _INVALID_DEADLINE_PATTERNS:
        if pat.search(candidate):
            return False
    if not _VALID_DEADLINE_ANCHORS.search(candidate):
        return False
    return True


# ── Task validation ─────────────────────────────────────────────────────
# Action verbs that signal a genuine task (checked after summarisation)
_ACTION_VERBS = re.compile(
    r"\b(handle|fix|write|create|update|review|deploy|test|configure"
    r"|audit|document|design|build|refactor|implement|prepare|set\s+up"
    r"|increase|add|draft|redesign|look\s+into|investigate|check"
    r"|monitor|migrate|integrate|optimize|schedule|resolve|improve"
    r"|analyze|coordinate|establish|run|send|submit|develop|maintain"
    r"|prioritize|track|validate|verify|follow\s+up|assign|escalate"
    r"|automate|define|map|plan|restore|rotate|enforce|assess)\b",
    re.I,
)

# Titles that are clearly NOT tasks (meta-talk, greetings, observations)
_NON_TASK_PATTERNS = [
    re.compile(r"^\s*good\s+(morning|afternoon|evening)\b", re.I),
    re.compile(r"^\s*(hi|hello|hey|welcome)\b", re.I),
    re.compile(r"\b(meet\s+again|schedule\s+(a\s+)?follow.?up)\b", re.I),
    re.compile(r"^\s*start\s+with\s+(the\s+)?sprint\b", re.I),
    re.compile(r"^\s*(sounds?\s+good|perfect|great|agreed)\b", re.I),
]


def _is_valid_task(title: str) -> bool:
    """Return True if a task title represents a genuine, actionable task."""
    if not title or len(title.split()) < 3:
        return False
    for pat in _NON_TASK_PATTERNS:
        if pat.search(title):
            return False
    if not _ACTION_VERBS.search(title):
        return False
    return True


class TaskGenerator:
    """
    Generates structured task objects from decision summaries.

    Uses ML models to extract:
    - assignee: person responsible (via QA model)
    - deadline: temporal expression (via NER model)

    Falls back to rule-based extraction when models are unavailable.
    """

    def __init__(self, qa_model_name: str = QA_MODEL_NAME):
        """
        Initialize task generator with QA and NER models.

        Args:
            qa_model_name: HuggingFace model for question answering.

        The constructor attempts to load:
        1. QA model (deepset/roberta-base-squad2) for assignee extraction
        2. spaCy NER model (en_core_web_sm) for deadline extraction

        Both gracefully degrade to rule-based fallbacks if unavailable.
        """
        self.qa_model_name = qa_model_name
        self._qa_model = None
        self._qa_tokenizer = None
        self._nlp = None  # spaCy pipeline for NER

        # ── Load QA model ───────────────────────────────────────────────
        try:
            print(f"[*] Loading QA model: {qa_model_name}")
            import torch
            from transformers import AutoTokenizer, AutoModelForQuestionAnswering

            torch.set_num_threads(1)
            self.device = torch.device("cpu")
            self._torch = torch

            self._qa_tokenizer = AutoTokenizer.from_pretrained(qa_model_name)
            self._qa_model = AutoModelForQuestionAnswering.from_pretrained(
                qa_model_name,
                dtype=torch.float32,
                low_cpu_mem_usage=False,
            )
            self._qa_model.to(self.device)
            self._qa_model.eval()
            print(f"[✓] QA model loaded (device: cpu)")
        except Exception as e:
            print(f"[!] Warning: Could not load QA model: {e}")
            print(f"[!] Falling back to speaker-based assignee extraction.")

        # ── Load spaCy NER model ────────────────────────────────────────
        try:
            print(f"[*] Loading spaCy NER model: en_core_web_sm")
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
            print(f"[✓] spaCy NER model loaded")
        except Exception as e:
            print(f"[!] Warning: Could not load spaCy NER: {e}")
            print(f"[!] Falling back to regex-based deadline extraction.")

    # ── Assignee Extraction ─────────────────────────────────────────────

    def _normalize_dialogue_for_qa(
        self, evidence_sentences: List[Dict]
    ) -> str:
        """
        Build QA context from evidence sentences with normalized dialogue.

        Transforms "Alice: Charlie, can you write the tests?" into
        "Alice said: Charlie, can you write the tests?" so that the
        QA model does not include the speaker tag in its answer span.

        Args:
            evidence_sentences: List of transcript sentence dicts.

        Returns:
            Normalized context string for QA inference.
        """
        parts = []
        for sent in evidence_sentences:
            speaker = sent.get("speaker", "")
            text = sent.get("text", "")
            # Use "said:" separator — prevents QA from merging speaker+name
            parts.append(f"{speaker} said: {text}")
        return " ".join(parts)

    def _clean_qa_answer(
        self, answer: str, known_speakers: List[str]
    ) -> str:
        """
        Clean a QA-predicted answer span to extract a valid speaker name.

        Handles cases where the model extracts spans like:
        - "Alice: Charlie" → "Charlie"
        - "Alice said: Charlie" → "Charlie"
        - "Charlie," → "Charlie"

        After cleaning, validates against known speakers from the transcript.

        Args:
            answer: Raw QA model answer string.
            known_speakers: List of speaker names from the transcript.

        Returns:
            Cleaned assignee name.
        """
        cleaned = answer.strip()

        # Strip "Speaker:" or "Speaker said:" prefix
        # Matches "Alice:", "Alice said:", "Bob :", etc.
        cleaned = re.sub(
            r"^\w+\s*(said\s*)?:\s*", "", cleaned, flags=re.IGNORECASE
        ).strip()

        # Strip trailing punctuation
        cleaned = cleaned.rstrip(".,;:!?").strip()

        # If the cleaned answer contains multiple words, try to find a
        # known speaker within it (e.g. "Charlie, can you" → "Charlie")
        if known_speakers:
            for speaker in known_speakers:
                if speaker.lower() in cleaned.lower():
                    return speaker

        # If still multi-word but no known speaker matched, take the
        # first word (often the name in "Charlie can you...")
        if " " in cleaned:
            first_word = cleaned.split()[0].rstrip(".,;:!?")
            # Only return it if it looks like a name (capitalized, >1 char)
            if first_word and first_word[0].isupper() and len(first_word) > 1:
                # Check against known speakers
                if known_speakers:
                    for speaker in known_speakers:
                        if speaker.lower() == first_word.lower():
                            return speaker
                return first_word

        return cleaned if cleaned else answer

    def _extract_assignee_qa(self, context: str) -> Optional[str]:
        """
        Extract the person responsible for the task using QA model.

        Asks the question "Who is responsible for performing this task?"
        against the evidence sentence context.

        Args:
            context: Evidence sentence text with speaker labels.

        Returns:
            Extracted name/speaker or None if confidence is too low.
        """
        if self._qa_model is None or self._qa_tokenizer is None:
            return None

        try:
            inputs = self._qa_tokenizer(
                QA_QUESTION,
                context,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with self._torch.no_grad():
                outputs = self._qa_model(**inputs)

            # Get start and end positions
            start_logits = outputs.start_logits
            end_logits = outputs.end_logits

            # roberta-base-squad2 can output "no answer" — check confidence
            # The [CLS] token (position 0) logit represents "no answer"
            start_idx = self._torch.argmax(start_logits, dim=-1).item()
            end_idx = self._torch.argmax(end_logits, dim=-1).item()

            # If both point to position 0, model says "no answer"
            if start_idx == 0 and end_idx == 0:
                return None

            # Ensure valid span
            if end_idx < start_idx:
                return None

            # Decode the answer span
            input_ids = inputs["input_ids"][0]
            answer_ids = input_ids[start_idx : end_idx + 1]
            answer = self._qa_tokenizer.decode(answer_ids, skip_special_tokens=True)
            answer = answer.strip()

            # Filter out empty or nonsensical answers
            if not answer or len(answer) > 50:
                return None

            return answer

        except Exception as e:
            print(f"    [!] QA extraction error: {e}")
            return None

    def _extract_assignee_fallback(
        self, evidence_sentences: List[Dict]
    ) -> str:
        """
        Fallback assignee extraction using speaker metadata.

        Strategy:
        - For "I will" / "I'll" / "I can" statements → speaker is assignee
        - For "can you" / "could you" questions → look at next sentence's
          speaker for the addressee (if available)
        - Default: return the speaker of the first evidence sentence

        Args:
            evidence_sentences: List of transcript sentence dicts.

        Returns:
            Speaker label (e.g., "A", "B", "C").
        """
        if not evidence_sentences:
            return "Unknown"

        # Check for self-assignment patterns ("I will", "I'll", "I can")
        self_assign_pattern = re.compile(
            r"\b(I will|I'll|I can|I am going to|I'm going to|let me)\b",
            re.IGNORECASE,
        )
        for sent in evidence_sentences:
            if self_assign_pattern.search(sent.get("text", "")):
                return sent["speaker"]

        # Check for delegation patterns ("can you", "could you")
        # First try to extract the named addressee:
        #   "Charlie, can you write..." → assignee = Charlie
        named_delegation = re.compile(
            r"^(\w+)[,]\s*(can|could|would|will)\s+you\b",
            re.IGNORECASE,
        )
        for sent in evidence_sentences:
            m = named_delegation.match(sent.get("text", ""))
            if m:
                return m.group(1)  # The named person

        # Generic delegation without name
        delegation_pattern = re.compile(
            r"\b(can you|could you|would you|will you)\b",
            re.IGNORECASE,
        )
        for sent in evidence_sentences:
            if delegation_pattern.search(sent.get("text", "")):
                # The speaker is delegating → assignee is the addressee
                # Without explicit names, we return the speaker as the
                # person who initiated the task (they own the follow-up)
                return sent["speaker"]

        # Default: speaker of first evidence sentence
        return evidence_sentences[0]["speaker"]

    def extract_assignee(
        self, context: str, evidence_sentences: List[Dict],
        known_speakers: Optional[List[str]] = None,
    ) -> str:
        """
        Extract assignee using QA model with fallback to speaker metadata.

        Args:
            context: Full context string for QA inference (normalized).
            evidence_sentences: List of transcript sentence dicts.
            known_speakers: List of speaker names from the transcript.

        Returns:
            Assignee string (name or speaker label).
        """
        speakers = known_speakers or []

        # Try ML extraction first
        qa_answer = self._extract_assignee_qa(context)
        if qa_answer:
            # Clean the QA answer — strip speaker prefixes, validate name
            cleaned = self._clean_qa_answer(qa_answer, speakers)
            if cleaned:
                return cleaned

        # Fallback to speaker-based extraction
        return self._extract_assignee_fallback(evidence_sentences)

    # ── Deadline Extraction ─────────────────────────────────────────────

    def _extract_deadline_ner(self, text: str) -> Optional[str]:
        """
        Extract deadline using spaCy NER.

        Looks for DATE and TIME entity labels in the text.

        Args:
            text: Text to search for temporal expressions.

        Returns:
            First DATE or TIME entity text, or None.
        """
        if self._nlp is None:
            return None

        try:
            doc = self._nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("DATE", "TIME"):
                    candidate = ent.text.strip()
                    if _is_valid_deadline(candidate):
                        return candidate
            return None
        except Exception as e:
            print(f"    [!] NER extraction error: {e}")
            return None

    def _extract_deadline_regex(self, text: str) -> Optional[str]:
        """
        Fallback deadline extraction using regex patterns.

        Matches common temporal expressions in meeting language.

        Args:
            text: Text to search for date/time patterns.

        Returns:
            First matched temporal expression, or None.
        """
        text_lower = text.lower()
        for pattern in DEADLINE_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Return the matched text with original capitalization
                start, end = match.span()
                return text[start:end].strip()
        return None

    def extract_deadline(self, summary: str, evidence_texts: List[str]) -> Optional[str]:
        """
        Extract deadline from summary and evidence sentences.

        Searches the summary first (cleaned text), then evidence sentences.

        Args:
            summary: Decision summary text.
            evidence_texts: List of raw evidence sentence texts.

        Returns:
            Deadline string or None.
        """
        # Search summary first (most reliable, already cleaned)
        deadline = self._extract_deadline_ner(summary)
        if deadline:
            return deadline

        # Search evidence sentences
        for text in evidence_texts:
            deadline = self._extract_deadline_ner(text)
            if deadline:
                return deadline

        # Regex fallback on summary
        deadline = self._extract_deadline_regex(summary)
        if deadline:
            return deadline

        # Regex fallback on evidence sentences
        for text in evidence_texts:
            deadline = self._extract_deadline_regex(text)
            if deadline:
                return deadline

        return None

    # ── Task Generation ─────────────────────────────────────────────────

    def generate_task(
        self,
        summary: Dict,
        transcript_sentences: List[Dict],
    ) -> Dict:
        """
        Generate a structured task from one decision summary.

        Args:
            summary: Dict with cluster_id, summary, evidence_sentences.
            transcript_sentences: Full list of transcript sentences (from STEP 1).

        Returns:
            Task dict with task_id, title, assignee, deadline,
            evidence_sentences, cluster_id.
        """
        cluster_id = summary["cluster_id"]
        summary_text = summary["summary"]
        evidence_ids = summary["evidence_sentences"]

        # Retrieve evidence sentences from transcript
        sentence_map = {s["sentence_id"]: s for s in transcript_sentences}
        evidence_sentences = [
            sentence_map[sid] for sid in evidence_ids if sid in sentence_map
        ]

        # Collect known speakers from the full transcript
        known_speakers = sorted(
            {s["speaker"] for s in transcript_sentences if s.get("speaker")}
        )

        # Build normalized context for QA — uses "said:" to prevent
        # the model from including speaker labels in the answer span
        qa_context = self._normalize_dialogue_for_qa(evidence_sentences)
        full_context = f"Task: {summary_text} Context: {qa_context}"

        # Extract assignee
        assignee = self.extract_assignee(
            full_context, evidence_sentences, known_speakers
        )
        print(f"  [{cluster_id}] Assignee: \"{assignee}\"")

        # Extract deadline
        evidence_texts = [s["text"] for s in evidence_sentences]
        deadline = self.extract_deadline(summary_text, evidence_texts)
        print(f"  [{cluster_id}] Deadline: {deadline if deadline else 'None'}")

        # Build title: remove trailing period from summary
        title = summary_text.rstrip(".")

        return {
            "task_id": cluster_id,
            "title": title,
            "assignee": assignee,
            "deadline": deadline,
            "evidence_sentences": evidence_ids,
            "cluster_id": cluster_id,
        }

    def generate_tasks(
        self,
        summaries: List[Dict],
        transcript_sentences: List[Dict],
    ) -> List[Dict]:
        """
        Generate structured tasks for all decision summaries.

        Args:
            summaries: List of decision summary dicts from STEP 4.
            transcript_sentences: Full transcript sentences from STEP 1.

        Returns:
            List of task dicts, one per summary.
        """
        print(f"\n[*] Generating tasks for {len(summaries)} summaries...")
        tasks = []
        skipped = 0
        for summary in summaries:
            task = self.generate_task(summary, transcript_sentences)
            if _is_valid_task(task["title"]):
                tasks.append(task)
            else:
                skipped += 1
                print(f"  [skip] Non-actionable task: {task['title'][:60]}...")

        # Re-number task IDs sequentially
        for i, task in enumerate(tasks, start=1):
            task["task_id"] = i

        print(f"[✓] Generated {len(tasks)} tasks ({skipped} rejected)")
        return tasks


# ── I/O helpers ─────────────────────────────────────────────────────────


def load_summaries(input_path: str) -> List[Dict]:
    """Load decision summaries from STEP 4 output."""
    with open(input_path, "r") as f:
        return json.load(f)


def load_transcript(input_path: str) -> List[Dict]:
    """Load transcript sentences from STEP 1 output."""
    with open(input_path, "r") as f:
        return json.load(f)


def save_tasks(tasks: List[Dict], output_path: str) -> None:
    """Save generated tasks as JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(tasks, f, indent=2)
    print(f"[✓] Tasks saved to: {output_path}")


def generate_tasks_from_transcript(
    summaries_path: str,
    transcript_path: str,
    output_path: str,
    qa_model_name: str = QA_MODEL_NAME,
) -> List[Dict]:
    """
    End-to-end: load summaries + transcript → generate tasks → save.

    Args:
        summaries_path: Path to decision summaries JSON (STEP 4 output).
        transcript_path: Path to transcript sentences JSON (STEP 1 output).
        output_path: Path to save tasks JSON (STEP 5 output).
        qa_model_name: QA model name for assignee extraction.

    Returns:
        List of task dicts.
    """
    print(f"\n[*] Loading decision summaries: {summaries_path}")
    summaries = load_summaries(summaries_path)
    print(f"[✓] Loaded {len(summaries)} summaries")

    print(f"\n[*] Loading transcript: {transcript_path}")
    transcript = load_transcript(transcript_path)
    print(f"[✓] Loaded {len(transcript)} sentences")

    generator = TaskGenerator(qa_model_name=qa_model_name)
    tasks = generator.generate_tasks(summaries, transcript)

    save_tasks(tasks, output_path)
    return tasks


# ── CLI entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    summaries_file = "data/decision_summaries/meeting1_decisions.json"
    transcript_file = "data/processed_transcripts/meeting1.json"
    output_file = "data/tasks/meeting1_tasks.json"

    print("=" * 70)
    print("STEP 5: TASK GENERATION")
    print("=" * 70)

    try:
        tasks = generate_tasks_from_transcript(
            summaries_path=summaries_file,
            transcript_path=transcript_file,
            output_path=output_file,
        )

        print("\n" + "=" * 70)
        print("GENERATED TASKS")
        print("=" * 70)

        for t in tasks:
            sids = ", ".join(str(sid) for sid in t["evidence_sentences"])
            print(f"\n  Task {t['task_id']}:")
            print(f"    Title:    {t['title']}")
            print(f"    Assignee: {t['assignee']}")
            print(f"    Deadline: {t['deadline'] if t['deadline'] else 'None'}")
            print(f"    Evidence: [{sids}]")
            print(f"    Cluster:  {t['cluster_id']}")

        print("\n" + "=" * 70)
        print(f"✓ Step 5 complete: {len(tasks)} tasks generated")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("  Make sure STEP 4 (summarization) has been run first")
