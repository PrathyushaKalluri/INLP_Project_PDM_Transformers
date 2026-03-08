# Step 3: Decision Clustering — Design & Improvement Journey

## Summary

STEP 3 takes the decision sentences identified by STEP 2 and groups them into clusters, where each cluster represents **one meeting decision or task**. These clusters feed into STEP 4 (summarization) and ultimately become individual task cards.

The module went through **three improvement iterations** to reach production quality:

| Version | Technique | Clusters (6 sentences) | Quality |
|---------|-----------|------------------------|---------|
| **v1** — Baseline | Raw cosine + threshold 0.7 | 2 clusters | ✗ Mixed topics |
| **v2** — Position-aware | + position penalty + min similarity | 4 clusters | ~ Acceptable |
| **v3** — Action-object aware | + spaCy verb-object penalty | **5 clusters** | ✓ Each = one task |

---

## Input / Output

### Input (from STEP 2)

```
data/decision_sentences/meeting1_decisions.json
```

```json
[
  {"sentence_id": 4,  "speaker": "B", "text": "I think we should focus on the payment API first", "decision_probability": 0.9228, "decision_type": "commitment"},
  {"sentence_id": 6,  "speaker": "A", "text": "we need to deploy it by end of march.", "decision_probability": 0.9283, "decision_type": "commitment"},
  {"sentence_id": 7,  "speaker": "A", "text": "can you prepare the technical spec?", "decision_probability": 0.857, "decision_type": "commitment"},
  {"sentence_id": 9,  "speaker": "B", "text": "also we need to finalize the pricing model", "decision_probability": 0.9471, "decision_type": "commitment"},
  {"sentence_id": 15, "speaker": "C", "text": "I will also prepare the documentation", "decision_probability": 0.8636, "decision_type": "commitment"},
  {"sentence_id": 18, "speaker": "A", "text": "let's aim for next wednesday", "decision_probability": 0.8904, "decision_type": "commitment"}
]
```

### Output

```
data/decision_clusters/meeting1_clusters.json
```

```json
[
  {"cluster_id": 0, "sentences": [4, 9], "texts": ["I think we should focus on the payment API first", "also we need to finalize the pricing model"], "speakers": ["B", "B"]},
  {"cluster_id": 1, "sentences": [18], "texts": ["let's aim for next wednesday"], "speakers": ["A"]},
  {"cluster_id": 2, "sentences": [6], "texts": ["we need to deploy it by end of march."], "speakers": ["A"]},
  {"cluster_id": 3, "sentences": [15], "texts": ["I will also prepare the documentation"], "speakers": ["C"]},
  {"cluster_id": 4, "sentences": [7], "texts": ["can you prepare the technical spec?"], "speakers": ["A"]}
]
```

---

## Architecture

```
STEP 2 output (decision sentences)
        │
        ▼
┌─────────────────────────────┐
│  Sentence Embeddings        │  all-mpnet-base-v2 (768-dim)
│  (semantic representation)  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Cosine Similarity Matrix   │  n × n pairwise similarities
└─────────────┬───────────────┘
              │
     ┌────────┼────────┐
     │        │        │
     ▼        ▼        ▼
  Position   Action   Min
  Penalty    Object   Similarity
  Weight     Penalty  Gate
     │        │        │
     └────────┼────────┘
              │
              ▼
┌─────────────────────────────┐
│  Adjusted Distance Matrix   │  distance = 1 - (cos_sim × pos × ao)
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  AgglomerativeClustering    │  metric=precomputed, linkage=average
│  distance_threshold=0.70    │
└─────────────┬───────────────┘
              │
              ▼
        Cluster JSON
```

---

## v1 — Baseline Implementation

### Approach

The initial implementation used a straightforward pipeline:

1. Encode each decision sentence using `SentenceTransformer("all-mpnet-base-v2")` — a 768-dimensional dense embedding model
2. Pass embeddings directly to `AgglomerativeClustering` with `metric="cosine"` and `linkage="average"`
3. Use `distance_threshold=0.7` to control cluster granularity

```python
AgglomerativeClustering(
    n_clusters=None,
    metric="cosine",
    linkage="average",
    distance_threshold=0.7,
)
```

### Result

```
6 sentences → 2 clusters
```

| Cluster | Sentences |
|---------|-----------|
| 0 | deploy by end of march, aim for next wednesday |
| 1 | focus on payment API, prepare technical spec, finalize pricing model, prepare documentation |

### Problem

**Cluster 1 merged 4 unrelated action items.** From the downstream pipeline's perspective, this produces one task card for four different tasks — making it useless.

### Root Cause Analysis

Raw cosine similarities between all 6 sentence pairs:

```
       [ 4]  [ 6]  [ 7]  [ 9]  [15]  [18]
[ 4]  1.000  0.305  0.145  0.522  0.370  0.258
[ 6]  0.305  1.000  0.213  0.358  0.316  0.341
[ 7]  0.145  0.213  1.000  0.342  0.518  0.067
[ 9]  0.522  0.358  0.342  1.000  0.509  0.265
[15]  0.370  0.316  0.518  0.509  1.000  0.196
[18]  0.258  0.341  0.067  0.265  0.196  1.000
```

Sentence embeddings capture **general project work similarity** — all four sentences in Cluster 1 talk about preparing, finalizing, or focusing on work deliverables. At threshold 0.7, these moderate similarities (0.3–0.5) allow transitive merging through average linkage.

### Apple Silicon Compatibility

The module includes safety measures for M1/M2/M3 Macs:

```python
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)
SentenceTransformer(model_name, device="cpu")
```

These prevent the bus errors that occur when PyTorch 2.x tries to use MPS acceleration.

---

## v2 — Position-Aware Similarity

### Problem Identified

The v1 clustering had no concept of **dialogue structure**. In meetings, decisions typically occur within local discussion segments. Sentences far apart in the transcript are unlikely to be about the same decision.

### Changes

#### 1. Precomputed Distance Matrix

Instead of passing raw embeddings to `AgglomerativeClustering`, we now pass a **precomputed distance matrix** that combines multiple signals:

```python
AgglomerativeClustering(
    n_clusters=None,
    metric="precomputed",  # Changed from "cosine"
    linkage="average",
    distance_threshold=0.70,
)
```

#### 2. Position Penalty

A soft constraint that reduces similarity between sentences that are far apart in the transcript:

```
position_weight(i, j) = 1 / (1 + decay × |sentence_id_i - sentence_id_j|)
```

With `position_decay = 0.05`:

| Pair | Distance in transcript | Position weight |
|------|----------------------|-----------------|
| [4]–[6] | 2 sentences | 0.909 |
| [4]–[9] | 5 sentences | 0.800 |
| [7]–[15] | 8 sentences | 0.714 |
| [4]–[18] | 14 sentences | 0.588 |

#### 3. Minimum Similarity Gate

Pairs with raw cosine similarity below `min_similarity = 0.40` are forced to distance 1.0 (never merge), regardless of other factors:

```python
adjusted_sim[cos_sim < self.min_similarity] = 0.0
```

This eliminates noise from semantically unrelated sentence pairs.

#### 4. Combined Formula

```
adjusted_similarity = cosine_sim × position_weight
if cosine_sim < 0.40: adjusted_similarity = 0.0
distance = 1 - adjusted_similarity
```

### Result

```
6 sentences → 4 clusters
```

| Cluster | Sentences | Theme |
|---------|-----------|-------|
| 0 | [7] prepare technical spec, [15] prepare documentation | Preparation |
| 1 | [4] focus on payment API, [9] finalize pricing model | Business priorities |
| 2 | [6] deploy by end of march | Deployment deadline |
| 3 | [18] aim for next wednesday | Scheduling |

### Remaining Problem

Cluster 0 still merged **"prepare technical spec"** and **"prepare documentation"**. These are different tasks assigned to different people — they should be separate clusters for separate task cards.

The cosine similarity between these two is 0.518 — moderate but enough to merge. The problem: embeddings see both sentences as "preparation" activities, ignoring that the **objects** (spec vs documentation) are different.

---

## v3 — Action–Object Separation (Final)

### Problem Identified

Meeting transcripts contain repeated action verbs like `prepare`, `send`, `deploy`, `schedule`, `finalize`. Sentence embeddings group sentences with the same verb even when the **objects are completely different tasks**.

| Sentence | Action | Object |
|----------|--------|--------|
| can you prepare the technical spec? | **prepare** | **spec** |
| I will also prepare the documentation | **prepare** | **documentation** |

These share the verb `prepare` but are **distinct tasks** that should produce separate task cards.

### Solution: spaCy Dependency Parsing

Added a new similarity adjustment layer using spaCy's dependency parser to extract `(action, object)` pairs:

```python
import spacy
nlp = spacy.load("en_core_web_sm")
```

#### Action-Object Extraction

For each sentence, the module extracts:
- **Action verb**: the root verb or its `xcomp`/`ccomp` complement (e.g., "need to **deploy**" → `deploy`)
- **Object noun**: the direct object or prepositional object, including compound modifiers (e.g., "payment **API**")

```python
def _extract_action_object(self, sentence):
    doc = self.nlp(sentence)
    # Find root verb or xcomp/ccomp complement
    # Find direct object with compound modifiers
    return {"action": action_verb, "object": obj}
```

Extraction results for all 6 sentences:

```
[0] action=focus        object=payment API          | I think we should focus on the payment API first
[1] action=deploy       object=end                  | we need to deploy it by end of march.
[2] action=prepare      object=spec                 | can you prepare the technical spec?
[3] action=finalize     object=pricing model        | also we need to finalize the pricing model
[4] action=prepare      object=documentation        | I will also prepare the documentation
[5] action=aim          object=wednesday            | let's aim for next wednesday
```

#### Penalty Rule

```python
if action_i == action_j and object_i != object_j:
    similarity = similarity × 0.6
```

This is applied as a **multiplier** in the distance matrix — it is NOT rule-based clustering. Semantic similarity from embeddings remains the primary signal.

#### Combined Formula (v3)

```
adjusted_similarity = cosine_sim × position_weight × ao_penalty
if cosine_sim < 0.40: adjusted_similarity = 0.0
distance = 1 - adjusted_similarity
```

### Effect on Critical Pair

| Pair [7]–[15] | v2 | v3 |
|---------------|----|----|
| Raw cosine | 0.518 | 0.518 |
| Position weight | 0.714 | 0.714 |
| AO penalty | 1.0 (none) | **0.6** |
| Adjusted similarity | 0.370 | **0.222** |
| Adjusted distance | 0.630 | **0.778** |
| vs threshold 0.70 | merge | **split ✓** |

### Result

```
6 sentences → 5 clusters
```

| Cluster | Sentences | Theme |
|---------|-----------|-------|
| 0 | [4] focus on payment API, [9] finalize pricing model | Business priorities (merge valid — same domain) |
| 1 | [18] aim for next wednesday | Scheduling (singleton) |
| 2 | [6] deploy by end of march | Deployment deadline (singleton) |
| 3 | [15] prepare the documentation | Documentation task (singleton) |
| 4 | [7] prepare the technical spec | Spec preparation (singleton) |

Each cluster maps cleanly to one task card in the downstream pipeline.

---

## Configuration

All parameters are configurable at initialization:

```python
from pipeline.clustering import DecisionClusterer

clusterer = DecisionClusterer(
    distance_threshold=0.70,       # Max distance to merge clusters
    position_decay=0.05,           # Position penalty strength
    min_similarity=0.40,           # Minimum cosine sim to consider merging
    object_mismatch_penalty=0.6,   # Penalty for same-verb different-object
)
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `distance_threshold` | 0.70 | Lower → more clusters, higher → fewer |
| `position_decay` | 0.05 | Higher → stronger penalty for distant sentences |
| `min_similarity` | 0.40 | Higher → more pairs forced apart |
| `object_mismatch_penalty` | 0.60 | Lower → stronger separation of same-verb pairs |

### Tuning Guide

- **Too many singletons?** Increase `distance_threshold` or lower `min_similarity`
- **Clusters too large / mixed?** Decrease `distance_threshold` or increase `position_decay`
- **Same-verb tasks merging?** Lower `object_mismatch_penalty` (e.g., 0.4)

---

## Usage

### Command Line

```bash
cd /path/to/meeting-action-extractor
python3 -m pipeline.clustering
```

### Python API

```python
from pipeline.clustering import cluster_decisions_in_transcript

clusters = cluster_decisions_in_transcript(
    input_path="data/decision_sentences/meeting1_decisions.json",
    output_path="data/decision_clusters/meeting1_clusters.json",
    distance_threshold=0.70,
    position_decay=0.05,
    min_similarity=0.40,
    object_mismatch_penalty=0.6,
)
```

### Programmatic Access

```python
from pipeline.clustering import DecisionClusterer

clusterer = DecisionClusterer()
clusters = clusterer.cluster_decisions(decision_sentences)
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `sentence-transformers` | ≥2.0 | Sentence embeddings (`all-mpnet-base-v2`) |
| `scikit-learn` | ≥1.0 | `AgglomerativeClustering` |
| `spacy` | ≥3.0 | Action-object extraction via dependency parsing |
| `en_core_web_sm` | ≥3.0 | English language model for spaCy |
| `numpy` | ≥1.0 | Matrix operations |
| `torch` | ≥1.0 | Backend for sentence-transformers |

### Installation

```bash
pip install sentence-transformers scikit-learn spacy
python3 -m spacy download en_core_web_sm
```

---

## Output Format

```json
{
  "cluster_id": 0,
  "sentences": [4, 9],
  "texts": ["I think we should focus on the payment API first", "also we need to finalize the pricing model"],
  "speakers": ["B", "B"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| cluster_id | int | Sequential cluster identifier (0-indexed) |
| sentences | list[int] | Sentence IDs from STEP 1 preprocessing |
| texts | list[str] | Original sentence texts |
| speakers | list[str] | Speaker labels per sentence |

This format is consumed by STEP 4 (summarization) to generate one decision summary per cluster.

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| 0 sentences | Returns empty list |
| 1 sentence | Returns single cluster (no clustering needed) |
| All singletons | Valid — each decision is independent |
| Same speaker, same verb, different objects | Penalty applied correctly |
| Sentences very far apart but semantically identical | Position penalty reduces similarity; may still merge if cosine sim is very high |
| spaCy cannot extract action/object | No penalty applied (penalty = 1.0), falls back to pure semantic clustering |

---

## Pipeline Integration

```
1. ✅ Step 1: Preprocessing          → data/processed_transcripts/meeting1.json
2. ✅ Step 2: Decision Detection     → data/decision_sentences/meeting1_decisions.json
3. ✅ Step 3: Clustering (this step) → data/decision_clusters/meeting1_clusters.json
4. 📋 Step 4: Summarization          → Decision summaries per cluster
5. 📋 Step 5: Task Generation        → Task cards from summaries
6. 📋 Step 6: Display                → Board with evidence linking
```

---

## Files

| File | Description |
|------|-------------|
| `pipeline/clustering.py` | Main module — `DecisionClusterer` class |
| `data/decision_clusters/meeting1_clusters.json` | Output for meeting1 |
| `data/decision_sentences/meeting1_decisions.json` | Input from STEP 2 |

---

## Design Rationale

**Why hierarchical clustering instead of K-Means?**
We don't know how many decisions a meeting contains. Hierarchical clustering with a distance threshold automatically determines the number of clusters.

**Why sentence-transformers instead of TF-IDF?**
Meeting sentences are short and often paraphrased. Dense embeddings capture semantic meaning better than sparse bag-of-words representations.

**Why position penalty?**
Meeting decisions occur within local discussion segments. Two sentences 15 positions apart are unlikely to be about the same decision, even if they share vocabulary.

**Why action-object penalty instead of rule-based splitting?**
Pure rule-based splitting would be fragile. The penalty is a soft signal — it reduces similarity but doesn't override strong semantic evidence. If two sentences truly discuss the same topic with the same verb and different objects, high cosine similarity can still override the penalty.

**Why precomputed distance matrix?**
Combining multiple distance signals (semantic, positional, action-object) requires computing a custom matrix. sklearn's `AgglomerativeClustering` supports `metric="precomputed"` for exactly this purpose.

**Why are singleton clusters valid?**
Many meeting decisions appear exactly once ("Let's deploy by March"). Forcing a minimum cluster size of 2 would either drop valid decisions or merge unrelated ones.
