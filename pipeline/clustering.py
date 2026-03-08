"""
Decision Clustering Module (STEP 3)

Groups decision-related sentences (from STEP 2) into clusters where each
cluster represents one meeting decision.

Methodology (follows spoken meeting decision summarization research):
1. Encode decision sentences as dense embeddings using sentence-transformers
2. Compute cosine similarity between sentence embeddings
3. Apply position-aware weighting — sentences far apart in the transcript
   are less likely to belong to the same decision
4. Apply action-object penalty — sentences sharing the same verb but
   different objects are penalized (e.g., "prepare spec" != "prepare docs")
5. Apply agglomerative (hierarchical) clustering with a strict distance
   threshold so each cluster represents a single decision or task
6. Output structured clusters with preserved sentence IDs for evidence linking

Why hierarchical clustering?
- Number of meeting decisions is unknown in advance
- Does not require a predefined cluster count
- Distance threshold is tunable per domain

Similarity adjustments (applied as multipliers before clustering):
- Position penalty:  1 / (1 + decay * |sid_i - sid_j|)
- Object mismatch:  x0.6 when same action verb but different object nouns
- Min similarity:   force apart pairs with raw cosine < threshold

Apple Silicon (M1/M2/M3) compatibility:
- Forces CPU device and disables tokenizer parallelism
- Limits torch threads to prevent bus errors
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

# ── Apple Silicon safety: set BEFORE importing torch/transformers ───────
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_COMPILE_DEBUG"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ── Configuration ───────────────────────────────────────────────────────
DISTANCE_THRESHOLD = 0.70          # Calibrated with position-aware distances
EMBEDDING_MODEL = "all-mpnet-base-v2"
POSITION_DECAY = 0.05              # Light position penalty for short transcripts
                                    # Higher = stronger penalty for distant sentences
MIN_SIMILARITY = 0.40              # Minimum raw cosine similarity to allow merging
                                    # Pairs below this forced apart regardless
OBJECT_MISMATCH_PENALTY = 0.6      # Similarity multiplier when same action, different object


class DecisionClusterer:
    """
    Groups decision sentences into clusters using semantic embeddings
    and agglomerative clustering with position-aware similarity
    and action-object separation.

    Each cluster represents one meeting decision or action item.
    """

    def __init__(
        self,
        distance_threshold: float = DISTANCE_THRESHOLD,
        model_name: str = EMBEDDING_MODEL,
        position_decay: float = POSITION_DECAY,
        min_similarity: float = MIN_SIMILARITY,
        object_mismatch_penalty: float = OBJECT_MISMATCH_PENALTY,
    ):
        """
        Initialize clusterer with sentence embedding model.

        Args:
            distance_threshold: Maximum inter-cluster distance for merging.
                                Lower = more clusters, higher = fewer clusters.
            model_name: sentence-transformers model identifier.
            position_decay: Controls strength of position penalty.
                            0.0 = no penalty, 0.1 = moderate, 0.5 = aggressive.
            min_similarity: Minimum semantic cosine similarity to allow merging.
                            Pairs below this are forced apart regardless of threshold.
            object_mismatch_penalty: Similarity multiplier when two sentences share
                            the same action verb but have different objects.
                            0.6 = reduce similarity by 40%.

        Raises:
            OSError: If embedding model cannot be loaded.
        """
        self.distance_threshold = distance_threshold
        self.model_name = model_name
        self.position_decay = position_decay
        self.min_similarity = min_similarity
        self.object_mismatch_penalty = object_mismatch_penalty

        # Lazy-load spaCy NLP model (lightweight, used for action-object extraction)
        self._nlp = None

        try:
            print(f"[*] Loading sentence embedding model: {model_name}")
            import torch
            from sentence_transformers import SentenceTransformer

            # Apple Silicon safety
            torch.set_num_threads(1)

            self.model = SentenceTransformer(model_name, device="cpu")
            print(f"[✓] Embedding model loaded (device: cpu)")
        except Exception as e:
            raise OSError(f"Failed to load embedding model: {e}")

    @property
    def nlp(self):
        """Lazy-load spaCy model on first use."""
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
            print(f"[✓] spaCy model loaded (action-object extraction)")
        return self._nlp

    def embed_sentences(self, texts: List[str]):
        """
        Generate dense embeddings for a list of sentences.

        Args:
            texts: Sentence strings to embed.

        Returns:
            numpy.ndarray: Shape (n_sentences, embedding_dim).
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=16,
        )
        return embeddings

    def _extract_action_object(self, sentence: str) -> Dict:
        """
        Extract the main action verb and its direct object from a sentence.

        Uses spaCy dependency parsing to find:
        - Root verb or its xcomp/ccomp complement (the "real" action)
        - Direct object noun (with compound modifiers for multi-word objects)

        Examples:
            "can you prepare the technical spec?" -> {action: "prepare", object: "spec"}
            "I will also prepare the documentation" -> {action: "prepare", object: "documentation"}
            "we need to deploy it by end of march" -> {action: "deploy", object: "end"}

        Args:
            sentence: Input sentence text.

        Returns:
            dict with keys 'action' (str|None) and 'object' (str|None).
        """
        doc = self.nlp(sentence)

        # Find root verb
        root_verb = None
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                root_verb = token.lemma_
                break

        # Prefer xcomp/ccomp verb (e.g., "need to deploy" -> deploy)
        action_verb = root_verb
        for token in doc:
            if token.dep_ in ("xcomp", "ccomp") and token.pos_ == "VERB":
                action_verb = token.lemma_
                break

        # Find direct object noun (with compound modifiers)
        obj = None
        for token in doc:
            if token.dep_ in ("dobj", "pobj") and token.pos_ in ("NOUN", "PROPN"):
                compounds = [c.text for c in token.children if c.dep_ == "compound"]
                obj = (" ".join(compounds) + " " + token.text).strip() if compounds else token.text
                break

        return {"action": action_verb, "object": obj}

    def _action_object_penalty_matrix(self, texts: List[str]):
        """
        Build an n x n penalty matrix based on action-object extraction.

        For each pair (i, j):
        - If same action verb but DIFFERENT object -> penalty (e.g., 0.6)
        - Otherwise -> no penalty (1.0)

        This prevents merging sentences like:
            "prepare the technical spec" + "prepare the documentation"
        which share the verb "prepare" but are different tasks.

        Args:
            texts: List of sentence strings.

        Returns:
            numpy.ndarray: n x n matrix of penalty multipliers (0.6 or 1.0).
            list[dict]: Extracted action-object pairs for logging.
        """
        import numpy as np

        n = len(texts)
        pairs = [self._extract_action_object(t) for t in texts]

        # Log extracted pairs
        print(f"[*] Action-object extraction:")
        for i, (text, pair) in enumerate(zip(texts, pairs)):
            a = str(pair["action"]) if pair["action"] else "None"
            o = str(pair["object"]) if pair["object"] else "None"
            print(f"    [{i}] action={a:<12s} object={o:<20s} | {text[:50]}")

        # Build penalty matrix
        penalty = np.ones((n, n), dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                a_i, o_i = pairs[i]["action"], pairs[i]["object"]
                a_j, o_j = pairs[j]["action"], pairs[j]["object"]

                # Same action, different object -> penalize
                if (a_i is not None and a_j is not None
                        and a_i == a_j
                        and o_i is not None and o_j is not None
                        and o_i.lower() != o_j.lower()):
                    penalty[i, j] = self.object_mismatch_penalty
                    penalty[j, i] = self.object_mismatch_penalty
                    print(f"    >> Penalty [{i}]-[{j}]: same action '{a_i}', "
                          f"different objects '{o_i}' vs '{o_j}' -> x{self.object_mismatch_penalty}")

        return penalty, pairs

    def _compute_distance_matrix(self, embeddings, sentence_ids: List[int], texts: List[str]):
        """
        Compute position-aware, action-object-aware distance matrix.

        Combines three signals:
        1. Cosine similarity from sentence embeddings (primary signal)
        2. Position penalty: reduces similarity for distant sentences
        3. Action-object penalty: reduces similarity when same verb, different object

        Formula:
            cos_sim(i,j)    = cosine_similarity(e_i, e_j)
            pos_weight(i,j) = 1 / (1 + decay * |sid_i - sid_j|)
            ao_penalty(i,j) = 0.6 if same_action & different_object, else 1.0
            adjusted_sim    = cos_sim * pos_weight * ao_penalty
            distance        = 1 - adjusted_sim

        Additionally: if raw cos_sim < min_similarity, distance is forced to 1.0.

        Args:
            embeddings: numpy array of shape (n, dim).
            sentence_ids: list of sentence_id values for position awareness.
            texts: list of sentence strings for action-object extraction.

        Returns:
            numpy.ndarray: Symmetric distance matrix of shape (n, n).
        """
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        n = len(embeddings)

        # Step 1: Semantic cosine similarity (n x n)
        cos_sim = cosine_similarity(embeddings)

        # Step 2: Position weight matrix
        sid_array = np.array(sentence_ids, dtype=float)
        pos_dist = np.abs(sid_array[:, None] - sid_array[None, :])
        pos_weight = 1.0 / (1.0 + self.position_decay * pos_dist)

        # Step 3: Action-object penalty matrix
        ao_penalty, _ = self._action_object_penalty_matrix(texts)

        # Step 4: Combined adjusted similarity
        adjusted_sim = cos_sim * pos_weight * ao_penalty

        # Step 5: Enforce minimum similarity — force apart dissimilar pairs
        adjusted_sim[cos_sim < self.min_similarity] = 0.0

        # Step 6: Convert similarity -> distance
        distance_matrix = 1.0 - adjusted_sim

        # Ensure diagonal is exactly 0 and matrix is non-negative
        np.fill_diagonal(distance_matrix, 0.0)
        distance_matrix = np.maximum(distance_matrix, 0.0)

        return distance_matrix

    def cluster_decisions(self, decision_sentences: List[Dict]) -> List[Dict]:
        """
        Cluster decision sentences by position-aware semantic similarity
        with action-object separation.

        Args:
            decision_sentences: List of dicts from STEP 2, each with keys:
                - sentence_id (int)
                - speaker (str)
                - text (str)
                - decision_probability (float)
                - decision_type (str, optional)

        Returns:
            List of cluster dicts, each with:
                - cluster_id (int)
                - sentences (list[int]): sentence IDs
                - texts (list[str]): sentence texts
                - speakers (list[str]): speaker labels
        """
        import numpy as np

        n = len(decision_sentences)

        # Edge case: 0 or 1 sentences — no clustering needed
        if n == 0:
            print("[*] No decision sentences to cluster.")
            return []

        if n == 1:
            s = decision_sentences[0]
            print("[*] Only 1 decision sentence — single cluster.")
            return [
                {
                    "cluster_id": 0,
                    "sentences": [s["sentence_id"]],
                    "texts": [s["text"]],
                    "speakers": [s["speaker"]],
                }
            ]

        # Extract data
        texts = [s["text"] for s in decision_sentences]
        sentence_ids = [s["sentence_id"] for s in decision_sentences]

        # Step 1: Generate sentence embeddings
        print(f"\n[*] Generating embeddings for {n} sentences...")
        embeddings = self.embed_sentences(texts)
        print(f"[✓] Embeddings shape: {embeddings.shape}")

        # Step 2: Compute adjusted distance matrix (position + action-object)
        print(f"[*] Computing adjusted distance matrix...")
        print(f"    position_decay={self.position_decay}, min_similarity={self.min_similarity}, ao_penalty={self.object_mismatch_penalty}")
        distance_matrix = self._compute_distance_matrix(embeddings, sentence_ids, texts)

        # Debug: log pairwise distances
        print(f"[*] Pairwise adjusted distances:")
        for i in range(n):
            for j in range(i + 1, n):
                sid_i, sid_j = sentence_ids[i], sentence_ids[j]
                dist = distance_matrix[i, j]
                merge = "merge" if dist < self.distance_threshold else "split"
                print(f"    [{sid_i}]-[{sid_j}]  dist={dist:.4f}  -> {merge}")

        # Step 3: Agglomerative clustering with precomputed distance matrix
        print(f"[*] Clustering with distance_threshold={self.distance_threshold}...")
        from sklearn.cluster import AgglomerativeClustering

        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="precomputed",
            linkage="average",
            distance_threshold=self.distance_threshold,
        )
        labels = clustering.fit_predict(distance_matrix)
        n_clusters = len(set(labels))
        print(f"[✓] Found {n_clusters} clusters")

        # Step 4: Group sentences by cluster label
        clusters_map: Dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            clusters_map.setdefault(int(label), []).append(idx)

        # Step 5: Build structured output
        clusters = []
        for new_id, (_, indices) in enumerate(sorted(clusters_map.items())):
            cluster = {
                "cluster_id": new_id,
                "sentences": [decision_sentences[i]["sentence_id"] for i in indices],
                "texts": [decision_sentences[i]["text"] for i in indices],
                "speakers": [decision_sentences[i]["speaker"] for i in indices],
            }
            clusters.append(cluster)

        # Print cluster summary
        for c in clusters:
            sids = ", ".join(str(s) for s in c["sentences"])
            size_label = "singleton" if len(c["sentences"]) == 1 else f"{len(c['sentences'])} sentences"
            print(f"  Cluster {c['cluster_id']}: [{sids}] ({size_label})")

        return clusters


# ── I/O helpers ─────────────────────────────────────────────────────────


def load_decision_sentences(input_path: str) -> List[Dict]:
    """Load decision sentences from STEP 2 output."""
    with open(input_path, "r") as f:
        return json.load(f)


def save_clusters(clusters: List[Dict], output_path: str) -> None:
    """Save cluster output as JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"[✓] Clusters saved to: {output_path}")


def cluster_decisions_in_transcript(
    input_path: str,
    output_path: str,
    distance_threshold: float = DISTANCE_THRESHOLD,
    position_decay: float = POSITION_DECAY,
    min_similarity: float = MIN_SIMILARITY,
    object_mismatch_penalty: float = OBJECT_MISMATCH_PENALTY,
) -> List[Dict]:
    """
    End-to-end: load STEP 2 output -> cluster -> save.

    Args:
        input_path: Path to decision sentences JSON (STEP 2 output).
        output_path: Path to save cluster JSON (STEP 3 output).
        distance_threshold: Clustering distance threshold.
        position_decay: Position penalty strength.
        min_similarity: Minimum cosine similarity for merging.
        object_mismatch_penalty: Penalty for same-action different-object pairs.

    Returns:
        List of cluster dicts.
    """
    print(f"\n[*] Loading decision sentences: {input_path}")
    sentences = load_decision_sentences(input_path)
    print(f"[✓] Loaded {len(sentences)} decision sentences")

    clusterer = DecisionClusterer(
        distance_threshold=distance_threshold,
        position_decay=position_decay,
        min_similarity=min_similarity,
        object_mismatch_penalty=object_mismatch_penalty,
    )
    clusters = clusterer.cluster_decisions(sentences)

    save_clusters(clusters, output_path)
    return clusters


# ── CLI entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    input_file = "data/decision_sentences/meeting1_decisions.json"
    output_file = "data/decision_clusters/meeting1_clusters.json"

    print("=" * 70)
    print("STEP 3: DECISION CLUSTERING (Position + Action-Object Aware)")
    print("=" * 70)

    try:
        clusters = cluster_decisions_in_transcript(
            input_path=input_file,
            output_path=output_file,
            distance_threshold=DISTANCE_THRESHOLD,
            position_decay=POSITION_DECAY,
            min_similarity=MIN_SIMILARITY,
            object_mismatch_penalty=OBJECT_MISMATCH_PENALTY,
        )

        print("\n" + "=" * 70)
        print("DECISION CLUSTERS")
        print("=" * 70)

        for cluster in clusters:
            print(f"\n── Cluster {cluster['cluster_id']} ──")
            for sid, text, speaker in zip(
                cluster["sentences"], cluster["texts"], cluster["speakers"]
            ):
                print(f"  [{sid}] {speaker}: {text}")

        print("\n" + "=" * 70)
        print(f"✓ Step 3 complete: {len(clusters)} decision clusters formed")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("  Make sure STEP 2 (decision detection) has been run first")
