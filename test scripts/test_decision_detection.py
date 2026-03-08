"""
Simple test of decision detection with multi-label zero-shot classification.
Uses manual model loading to avoid HuggingFace pipeline() bus errors on Apple Silicon.
This is a standalone test to verify the pipeline works.
"""

import json
import os
from pathlib import Path

# ── Apple Silicon safety: set BEFORE importing torch/transformers ───────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_COMPILE_DEBUG"] = "0"

# Import shared configuration constants
from pipeline.decision_detector import (
    CLASSIFICATION_LABELS,
    LABEL_TO_TYPE,
    KEEP_TYPES,
    DECISION_THRESHOLD,
    MODEL_NAME,
)


def main():
    print("=" * 70)
    print("STEP 2: DECISION DETECTION TEST (Multi-Label)")
    print("=" * 70)

    # Load preprocessed transcript
    print("\n[1] Loading preprocessed transcript...")
    with open("data/processed_transcripts/meeting1.json", "r") as f:
        sentences = json.load(f)
    print(f"[✓] Loaded {len(sentences)} sentences")

    # Load model manually (avoids pipeline() bus error on Apple Silicon)
    print("\n[2] Initializing zero-shot classifier...")
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        # Apple Silicon safety
        torch.set_num_threads(1)
        device = torch.device("cpu")

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=False,
        )
        model.to(device)
        model.eval()

        # Detect entailment index
        id2label = model.config.id2label
        entailment_idx = None
        for idx, label in id2label.items():
            if label.lower() == "entailment":
                entailment_idx = int(idx)
                break
        if entailment_idx is None:
            entailment_idx = len(id2label) - 1

        print(f"[✓] Classifier loaded (model: {MODEL_NAME}, entailment idx: {entailment_idx})")
    except Exception as e:
        print(f"[✗] Error loading classifier: {e}")
        return

    # Helper: run NLI for one sentence
    def classify_sentence(text):
        hypotheses = [f"This text is {label}." for label in CLASSIFICATION_LABELS]
        scores = []
        for hypothesis in hypotheses:
            inputs = tokenizer(
                text,
                hypothesis,
                return_tensors="pt",
                truncation=True,
                max_length=256,
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)
                scores.append(probs[0, entailment_idx].item())

        # Normalize scores
        total = sum(scores)
        if total > 0:
            scores = [s / total for s in scores]

        best_idx = scores.index(max(scores))
        return LABEL_TO_TYPE[CLASSIFICATION_LABELS[best_idx]], scores[best_idx]

    # Classify sentences (batch_size=1 for memory safety)
    THRESHOLD = DECISION_THRESHOLD
    total = len(sentences)
    print(f"\n[3] Classifying {total} sentences...")

    decisions = []

    for idx, sentence in enumerate(sentences):
        text = sentence["text"]

        try:
            dtype, score = classify_sentence(text)

            if dtype in KEEP_TYPES and score > THRESHOLD:
                decisions.append({
                    **sentence,
                    "decision_probability": round(score, 4),
                    "decision_type": dtype,
                })

            # Progress
            if (idx + 1) % 5 == 0 or (idx + 1) == total:
                print(f"  [{idx + 1}/{total}] Processed...")

        except Exception as e:
            print(f"  [!] Error on sentence {idx + 1}: {e}")
            continue

    print(f"[✓] Classification complete")
    print(f"[✓] Found {len(decisions)} decision candidates")

    # Save output
    print(f"\n[4] Saving decision sentences...")
    output_dir = Path("data/decision_sentences")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "meeting1_decisions.json"
    with open(output_path, "w") as f:
        json.dump(decisions, f, indent=2)

    print(f"[✓] Saved to: {output_path}")

    # Display results
    print("\n[5] DETECTED DECISIONS")
    print("-" * 70)

    for i, decision in enumerate(decisions[:5], 1):
        print(f"\nDecision #{i}")
        print(f"  ID:         {decision['sentence_id']}")
        print(f"  Speaker:    {decision['speaker']}")
        print(f"  Text:       {decision['text']}")
        print(f"  Type:       {decision['decision_type']}")
        print(f"  Confidence: {decision['decision_probability']:.1%}")

    if len(decisions) > 5:
        print(f"\n... and {len(decisions) - 5} more decisions")

    # Statistics
    print("\n[6] STATISTICS")
    print("-" * 70)

    detection_rate = len(decisions) / len(sentences) * 100

    print(f"  Total sentences: {len(sentences)}")
    print(f"  Decisions found: {len(decisions)}")
    print(f"  Detection rate:  {detection_rate:.1f}%")

    # By decision type
    type_counts = {}
    for decision in decisions:
        t = decision["decision_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n  By decision type:")
    for dtype in sorted(type_counts.keys()):
        count = type_counts[dtype]
        print(f"    {dtype}: {count}")

    # By speaker
    speaker_counts = {}
    for decision in decisions:
        speaker = decision["speaker"]
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    print(f"\n  Decisions by speaker:")
    for speaker in sorted(speaker_counts.keys()):
        count = speaker_counts[speaker]
        print(f"    {speaker}: {count}")

    # Confidence
    if decisions:
        confidences = [d["decision_probability"] for d in decisions]
        print(f"\n  Confidence stats:")
        print(f"    Min:  {min(confidences):.1%}")
        print(f"    Max:  {max(confidences):.1%}")
        print(f"    Mean: {sum(confidences) / len(confidences):.1%}")

    print("\n" + "=" * 70)
    print("✓ Step 2 complete: Decision detection finished")
    print("=" * 70)


if __name__ == "__main__":
    main()
