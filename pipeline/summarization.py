"""
Decision Summarization Module (STEP 4)

Converts clusters of decision sentences (from STEP 3) into concise,
action-oriented task statements using an instruction-tuned language model.

Methodology:
1. Load decision clusters from STEP 3
2. Build an instruction prompt with all cluster sentences
3. Ask FLAN-T5 to generate a single imperative action item
4. Validate the output contains an action verb
5. Fall back to rule-based cleaning only if model is unavailable
6. Post-process: capitalize proper nouns/dates, ensure punctuation

Why FLAN-T5?
- Instruction-tuned: understands "convert this into a task" prompts
- Works well with short inputs (unlike distilbart-cnn which needs long articles)
- Generates concise imperative sentences naturally
- ~990MB model, runs comfortably on Apple Silicon CPU

Apple Silicon (M1/M2/M3) compatibility:
- Uses google/flan-t5-base (~990MB)
- Manual model loading with CPU device
- Single-threaded torch inference
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
MODEL_NAME = "google/flan-t5-base"  # Instruction-tuned T5 (~990MB)

# Instruction prompt template for task extraction
TASK_PROMPT = (
    "Convert the following meeting discussion into one short action item. "
    "Remove names, pronouns, and conversational language. "
    "Start with an imperative verb. Output only one sentence.\n\n"
    "Discussion:\n{cluster_text}\n\n"
    "Action item:"
)

# Action verbs that signal a genuine task
ACTION_VERBS = re.compile(
    r"\b(handle|fix|write|create|update|review|deploy|test|configure"
    r"|audit|document|design|build|refactor|implement|prepare|set\s+up"
    r"|increase|add|draft|redesign|look\s+into|investigate|check"
    r"|monitor|migrate|integrate|optimize|schedule|resolve|improve"
    r"|analyze|coordinate|establish|run|send|submit|develop|maintain"
    r"|prioritize|track|validate|verify|follow\s+up|assign|escalate"
    r"|automate|define|map|plan|restore|rotate|enforce|assess)\b",
    re.I,
)

# Non-task patterns — outputs matching these are rejected
NON_TASK_PATTERNS = [
    re.compile(r"^\s*good\s+(morning|afternoon|evening)\b", re.I),
    re.compile(r"^\s*(hi|hello|hey|welcome|thanks?|thank\s+you)\b", re.I),
    re.compile(r"^\s*(sounds?\s+good|perfect|great|agreed|sure|okay|ok)\b", re.I),
    re.compile(r"\b(meet\s+again|schedule\s+(a\s+)?follow.?up)\b", re.I),
    re.compile(r"^\s*start\s+with\s+(the\s+)?(sprint|meeting|standup)\b", re.I),
]

# Conversational prefixes to strip (used in rule-based fallback)
CONVERSATIONAL_PATTERNS = [
    r"^I think we should\s+",
    r"^I think we need to\s+",
    r"^I think\s+",
    r"^we should\s+",
    r"^we need to\s+",
    r"^we have to\s+",
    r"^also we need to\s+",
    r"^also we should\s+",
    r"^also\s+",
    r"^let'?s\s+",
    r"^can you\s+",
    r"^could you\s+",
    r"^would you\s+",
    r"^I will also\s+",
    r"^I will\s+",
    r"^I'll\s+",
    r"^I am going to\s+",
    r"^maybe we should\s+",
    r"^maybe\s+",
    r"^please\s+",
    r"^(yes|sure|agreed|absolutely|definitely)[,.]?\s*(I\s+(will|can|'ll)\s+)?",
    r"^\w+[,]\s*(can|could|would|will)\s+you\s+",
    r"^let\s+me\s+",
    r"^let\s+us\s+",
    r"^I need to\s+",
    r"^I have to\s+",
    r"^I'?m\s+going\s+to\s+",
    r"^we'?ll\s+",
]

# Filler words to remove (word-boundary safe)
FILLER_WORDS = [
    r"\bfirst\b",
    r"\bjust\b",
    r"\bactually\b",
    r"\bbasically\b",
    r"\bprobably\b",
    r"\bdefinitely\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\byeah\b",
    r"\bokay\b",
    r"\blike\b(?!\s+\w+ing)",
]

# Days and months for capitalization
DAYS_OF_WEEK = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def _is_actionable(text: str) -> bool:
    """Return True if the text contains an action verb and is not meta-talk."""
    if not text or len(text.split()) < 3:
        return False
    for pat in NON_TASK_PATTERNS:
        if pat.search(text):
            return False
    return bool(ACTION_VERBS.search(text))


class DecisionSummarizer:
    """
    Generates concise decision summaries from sentence clusters.

    Uses FLAN-T5 instruction prompting to convert meeting discussion
    into imperative action items.  Falls back to rule-based cleaning
    only when the model is unavailable.
    """

    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize summarizer with FLAN-T5 instruction-tuned model.

        Args:
            model_name: HuggingFace model for instruction-based generation.
                        Default: google/flan-t5-base.
        """
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

        try:
            print(f"[*] Loading summarization model: {model_name}")
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            # Apple Silicon safety
            torch.set_num_threads(1)
            self.device = torch.device("cpu")

            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                dtype=torch.float32,
                low_cpu_mem_usage=False,
            )
            self._model.to(self.device)
            self._model.eval()
            print(f"[✓] Summarization model loaded (device: cpu)")
        except Exception as e:
            print(f"[!] Warning: Could not load summarization model: {e}")
            print(f"[!] Falling back to rule-based cleaning only.")

    # ── Rule-based cleaning (fallback) ──────────────────────────────────

    def _clean_to_task_statement(self, text: str) -> str:
        """
        Clean a sentence into a task-style statement via regex rules.

        Used as fallback when the model is unavailable.

        Args:
            text: Raw sentence text.

        Returns:
            Cleaned task-style statement.
        """
        cleaned = text.strip()

        # Keep only the first sentence (model may concatenate multiple)
        for sep in [". ", "? ", "! "]:
            if sep in cleaned:
                cleaned = cleaned[:cleaned.index(sep)].strip()

        # Remove conversational prefixes (two passes)
        for pattern in CONVERSATIONAL_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        for pattern in CONVERSATIONAL_PATTERNS:
            bare_pattern = pattern.replace(r"\s+", r"\s*")
            cleaned = re.sub(bare_pattern + "$", "", cleaned, flags=re.IGNORECASE).strip()

        # Remove filler words
        for pattern in FILLER_WORDS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # Collapse multiple spaces
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

        # Remove trailing question mark / period
        cleaned = cleaned.rstrip("?").rstrip(".").strip()

        # Capitalize days of the week
        for day in DAYS_OF_WEEK:
            cleaned = re.sub(
                rf"\b{day}\b", day.capitalize(), cleaned, flags=re.IGNORECASE
            )

        # Capitalize months
        for month in MONTHS:
            cleaned = re.sub(
                rf"\b{month}\b", month.capitalize(), cleaned, flags=re.IGNORECASE
            )

        # Capitalize first letter (action verb)
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        # Ensure ends with period
        if cleaned and not cleaned.endswith("."):
            cleaned += "."

        return cleaned

    # ── Model-based generation ──────────────────────────────────────────

    def _generate_task_summary(self, cluster_texts: List[str]) -> Optional[str]:
        """
        Generate an action-item summary using FLAN-T5 instruction prompting.

        Builds a prompt with all cluster sentences and asks the model to
        produce a single imperative sentence starting with a verb.

        Args:
            cluster_texts: List of raw sentence texts in the cluster.

        Returns:
            Generated task string, or None if model is unavailable.
        """
        if self._model is None or self._tokenizer is None:
            return None

        import torch

        # Build instruction prompt with full cluster context
        discussion = "\n".join(cluster_texts)
        prompt = TASK_PROMPT.format(cluster_text=discussion)

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            output_ids = self._model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=40,
                num_beams=4,
                repetition_penalty=1.2,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )

        summary = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return summary.strip()

    def _postprocess(self, text: str) -> str:
        """
        Post-process model output: capitalize dates, ensure punctuation.

        Args:
            text: Raw model output.

        Returns:
            Polished task statement.
        """
        cleaned = text.strip().rstrip(".")

        # Capitalize days
        for day in DAYS_OF_WEEK:
            cleaned = re.sub(
                rf"\b{day}\b", day.capitalize(), cleaned, flags=re.IGNORECASE
            )
        # Capitalize months
        for month in MONTHS:
            cleaned = re.sub(
                rf"\b{month}\b", month.capitalize(), cleaned, flags=re.IGNORECASE
            )

        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        # Ensure trailing period
        if cleaned and not cleaned.endswith("."):
            cleaned += "."

        return cleaned

    # ── Cluster summarization ───────────────────────────────────────────

    def summarize_cluster(self, cluster: Dict) -> Dict:
        """
        Generate a decision summary for one cluster.

        Strategy:
        1. Send all cluster sentences to FLAN-T5 via instruction prompt
        2. Validate the output is actionable (contains an action verb)
        3. If model output is not actionable or model is unavailable,
           fall back to rule-based cleaning of the best sentence

        Args:
            cluster: Dict with keys cluster_id, sentences, texts, speakers.

        Returns:
            Dict with cluster_id, summary, evidence_sentences.
        """
        texts = cluster["texts"]
        cluster_id = cluster["cluster_id"]
        sentence_ids = cluster["sentences"]

        summary = None

        # ── Try model-based generation ──────────────────────────────────
        if self._model is not None:
            raw = self._generate_task_summary(texts)
            if raw:
                # Clean model output the same way we clean raw sentences —
                # strips "I will", "can you", names, etc. then capitalises
                processed = self._clean_to_task_statement(raw)
                if _is_actionable(processed):
                    summary = processed
                    print(f"  [{cluster_id}] (model) raw=\"{raw}\" → \"{processed}\"")
                else:
                    print(f"  [{cluster_id}] Model output not actionable: \"{raw}\" → fallback")

        # ── Fallback: rule-based cleaning ───────────────────────────────
        if summary is None:
            cleaned = [self._clean_to_task_statement(t) for t in texts]
            # Prefer sentences with action verbs; among those pick longest
            actionable = [s for s in cleaned if _is_actionable(s)]
            if actionable:
                summary = max(actionable, key=len)
            else:
                summary = max(cleaned, key=len) if cleaned else ""
            print(f"  [{cluster_id}] (rule)  \"{summary}\"")

        return {
            "cluster_id": cluster_id,
            "summary": summary,
            "evidence_sentences": sentence_ids,
        }

    def summarize_clusters(self, clusters: List[Dict]) -> List[Dict]:
        """
        Generate decision summaries for all clusters.

        Args:
            clusters: List of cluster dicts from STEP 3.

        Returns:
            List of summary dicts, one per cluster.
        """
        print(f"\n[*] Summarizing {len(clusters)} clusters...")
        summaries = []
        for cluster in clusters:
            summary = self.summarize_cluster(cluster)
            summaries.append(summary)

        print(f"[✓] Generated {len(summaries)} decision summaries")
        return summaries


# ── I/O helpers ─────────────────────────────────────────────────────────


def load_clusters(input_path: str) -> List[Dict]:
    """Load clusters from STEP 3 output."""
    with open(input_path, "r") as f:
        return json.load(f)


def save_summaries(summaries: List[Dict], output_path: str) -> None:
    """Save decision summaries as JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summaries, f, indent=2)
    print(f"[✓] Summaries saved to: {output_path}")


def summarize_decisions_in_transcript(
    input_path: str,
    output_path: str,
    model_name: str = MODEL_NAME,
) -> List[Dict]:
    """
    End-to-end: load STEP 3 clusters → summarize → save.

    Args:
        input_path: Path to cluster JSON (STEP 3 output).
        output_path: Path to save summary JSON (STEP 4 output).
        model_name: Summarization model name.

    Returns:
        List of summary dicts.
    """
    print(f"\n[*] Loading clusters: {input_path}")
    clusters = load_clusters(input_path)
    print(f"[✓] Loaded {len(clusters)} clusters")

    summarizer = DecisionSummarizer(model_name=model_name)
    summaries = summarizer.summarize_clusters(clusters)

    save_summaries(summaries, output_path)
    return summaries


# ── CLI entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    input_file = "data/decision_clusters/meeting1_clusters.json"
    output_file = "data/decision_summaries/meeting1_decisions.json"

    print("=" * 70)
    print("STEP 4: DECISION SUMMARIZATION")
    print("=" * 70)

    try:
        summaries = summarize_decisions_in_transcript(
            input_path=input_file,
            output_path=output_file,
        )

        print("\n" + "=" * 70)
        print("DECISION SUMMARIES")
        print("=" * 70)

        for s in summaries:
            sids = ", ".join(str(sid) for sid in s["evidence_sentences"])
            print(f"\n  Cluster {s['cluster_id']}:")
            print(f"    Summary:  {s['summary']}")
            print(f"    Evidence: [{sids}]")

        print("\n" + "=" * 70)
        print(f"✓ Step 4 complete: {len(summaries)} decision summaries generated")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("  Make sure STEP 3 (clustering) has been run first")
