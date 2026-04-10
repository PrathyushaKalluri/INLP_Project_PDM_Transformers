# NLP Pipeline Methodology

**Project:** PDM Transformers — Meeting Action Extraction  
**Version:** 2.0 (post-refactoring)  
**Last Updated:** April 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Stage 1 — Preprocessing](#3-stage-1--preprocessing)
   - 3.1 Speaker Parsing
   - 3.2 Sentence Splitting & Linguistic Metadata
   - 3.3 Text Cleaning & Indian English Normalisation
   - 3.4 Stopword Filtering
   - 3.5 SVO Triplet Resolution
   - 3.6 Sentence Type Flagging
   - 3.7 Meeting Type Detection
4. [Stage 2 — Decision Detection](#4-stage-2--decision-detection)
   - 4.1 Rule-Based Pre-filter
   - 4.2 Hard Filters
   - 4.3 Transformer-Based Classification (NLI)
   - 4.4 Feature Fusion
   - 4.5 Turn-Pair Acceptance Detector
5. [Stage 3 — Metadata Extraction](#5-stage-3--metadata-extraction)
   - 5.1 Assignee Extraction
   - 5.2 Deadline Extraction
6. [Stage 4 — Postprocessing](#6-stage-4--postprocessing)
   - 6.1 Task Title Generation
   - 6.2 Confidence Scoring
   - 6.3 Task Validation
   - 6.4 Deduplication
7. [Design Choices & Rationale](#7-design-choices--rationale)
8. [Changes Made in v2.0](#8-changes-made-in-v20)
9. [Known Limitations & Future Work](#9-known-limitations--future-work)

---

## 1. Overview

This pipeline extracts structured action items from raw meeting transcripts. Given an unstructured conversational text between named participants, it identifies every statement that represents a task, commitment, or decision, and returns a structured list of:

```json
{
  "task_id": "task_1",
  "task": "Handle the API refactor.",
  "assignee": "Bob",
  "deadline": "Friday",
  "confidence": 0.89,
  "evidence": {
    "text": "I will handle the API refactor by Friday.",
    "speaker": "Bob"
  }
}
```

The pipeline is built around four sequential stages, each independently testable, with a shared configuration module controlling all model names and thresholds.

---

## 2. System Architecture

```
Raw Transcript (str)
        │
        ▼
┌─────────────────────────────────┐
│  STAGE 1: PREPROCESSING         │
│  • parse_speakers               │
│  • split_sentences (spaCy)      │
│  • clean_sentences              │
│  • filter_stopwords             │
│  • resolve_triplets (SVO)       │
│  • flag_sentence_types          │
│  • detect_meeting_type          │
└─────────────┬───────────────────┘
              │  List[SentenceDict]  (+ meeting_type)
              ▼
┌─────────────────────────────────┐
│  STAGE 2: DECISION DETECTION    │
│  • RuleBasedDetector            │
│  • DependencyFeatureAnalyzer    │
│    (hard filter + modal boost)  │
│  • EnhancedTransformerClassifier│
│    (NLI + context window)       │
│  • TurnPairAcceptanceDetector   │
└─────────────┬───────────────────┘
              │  List[SentenceDict]  (is_decision=True)
              ▼
┌─────────────────────────────────┐
│  STAGE 3: METADATA EXTRACTION   │
│  • AssigneeExtractor            │
│    (rules → QA model fallback)  │
│  • DeadlineExtractor            │
│    (spaCy NER → regex fallback) │
└─────────────┬───────────────────┘
              │  List[TaskDefinition]
              ▼
┌─────────────────────────────────┐
│  STAGE 4: POSTPROCESSING        │
│  • TaskBuilder (title gen.)     │
│  • ConfidenceScorer             │
│  • TaskValidator                │
│  • Deduplicator (semantic)      │
└─────────────┬───────────────────┘
              │
              ▼
        List[Task]  (JSON output)
```

**Entry points:**
- `run_pipeline.py` — CLI tool, per-meeting use, saves intermediate JSON per stage
- `pipeline/pipeline.py` (`NLPActionExtractor`) — Python API, reusable class for batch use

**Configuration:** All model names, thresholds, and paths live in `pipeline/config.py`.

---

## 3. Stage 1 — Preprocessing

### 3.1 Speaker Parsing

**Module:** `pipeline/preprocessing/speaker_parser.py`

The raw transcript is first parsed into a sequence of `(speaker, utterance)` turns. Three formats are supported:

| Format | Example |
|--------|---------|
| Colon | `Alice: I'll handle this by Friday.` |
| Dash | `Alice - I'll handle this by Friday.` |
| Timestamp | `[00:03:12] Alice: I'll handle this by Friday.` |

Each turn becomes a `dict` with keys `turn_id`, `speaker`, `timestamp` (or `None`), and `text`. A set of unique speaker names is extracted here and propagated downstream for use in assignee resolution.

**Design choice:** Parsing happens before sentence splitting so that speaker identity is attached to every sentence from the start. This avoids the expensive alternative of re-identifying speakers mid-document.

---

### 3.2 Sentence Splitting & Linguistic Metadata

**Module:** `pipeline/preprocessing/sentence_splitter.py`

Each utterance is tokenised and split into individual sentences using spaCy's `en_core_web_sm` dependency parser. For each sentence, the parser extracts a lightweight structural triplet:

| Field | Description | Example |
|-------|-------------|---------|
| `root_verb` | Lemma of the main/principal verb | `"deploy"` |
| `subject` | Subject noun phrase or speaker fallback | `"Bob"` |
| `object` | Best direct-object noun phrase | `"the API"` |

**Root verb resolution:** If the ROOT token is a modal or weak auxiliary (`will`, `should`, `have`, `let`, etc.), the parser walks to the first non-auxiliary child verb (`xcomp`, `ccomp`, `advcl`) to find the actual semantic verb.

**Object resolution strategy:** A priority-ranked candidate list is maintained: `dobj/obj` (highest) → `iobj` → `attr` → `pobj` (lowest, only non-temporal). Pronouns are de-prioritised over nouns at the same priority level. Temporal prepositional objects (`by Friday`, `before Monday`) are explicitly excluded.

**Subject fallback:** If no syntactic subject is found and the sentence is not passive, the speaker name is used as the default subject.

**Design choice:** Linguistic metadata is extracted once at the sentence level and cached in the sentence dict. Every downstream module can then access `root_verb`, `subject`, and `object` without re-parsing, avoiding repeated inference on the same text.

---

### 3.3 Text Cleaning & Indian English Normalisation

**Module:** `pipeline/preprocessing/cleaner.py`

Two cleaning passes are applied:

1. **Whitespace normalisation** — collapses multiple spaces, trims edges.
2. **Filler word removal** — removes `um`, `uh` unconditionally. The word `like` is removed **only** when it is clearly a discourse filler (followed by a pronoun or discourse marker like `I`, `we`, `so`, `yeah`), not when it appears as a preposition (`tools like Kubernetes`) or verb.
3. **Indian English normalisation** — maps domain-specific idioms to standard equivalents:

| Indian English | Standard |
|---|---|
| `prepone` | `move earlier` |
| `do the needful` | `take necessary action` |
| `revert back` | `reply` |
| `kindly` | *(removed)* |
| `pls` / `pl` | `please` |
| `asap` | `as soon as possible` |

**Change in v2.0:** The original filler regex `\blike\b(?!\s+\w+ing)` only excluded gerunds, incorrectly stripping "like" from noun phrase uses. Replaced with a context-sensitive lookahead that only matches filler "like" followed by pronouns or discourse markers.

---

### 3.4 Stopword Filtering

**Module:** `pipeline/preprocessing/stopword_filter.py`

Before expensive transformer inference, clearly non-actionable sentences are removed using pattern matching. Categories filtered:

- **Greetings & closings:** `Good morning everyone`, `Thanks all`, `Have a good week`
- **Single-word confirmations:** `Yes.`, `Ok.`, `Sure.`, `Agreed.`
- **Meta-conversation:** `Anyway,`, `One last thing`, `Quick standup`
- **Reactions & assessments:** `Good idea`, `I agree`, `That's great`
- **Pure questions with no action intent:** `Anything else?`, `What's your status?`
- **Colloquialisms:** `Got it`, `Will do`, `No problem`

**Design choice:** Running a pattern filter before the transformer classifier eliminates obvious noise early, reducing the number of sentences that need expensive neural inference by typically 30–50%.

---

### 3.5 SVO Triplet Resolution

**Module:** `pipeline/preprocessing/triplet_resolver.py`

Raw triplets from the sentence splitter are refined through 9 sequential fixes to handle conversational language edge cases:

| Fix | Problem Addressed | Example |
|-----|-------------------|---------|
| 1. Direct object boundary | Prevent traversal into subclauses | "I decided [that we should fix it]" → obj: `it`, not clause |
| 2. Conjunction handling | Pick root verb's object first | "Fix [bug] and test" → obj: `bug` |
| 3. Temporal pobj filter | Exclude time phrases as objects | "Deploy by Friday" → no object (not "Friday") |
| 4. Anaphora resolution | Carry-forward pronoun resolution | "Fix it" (after "found the bug") → obj: `bug` |
| 5. "you" subject resolution | Map "you" to named addressee | "Charlie, can you write..." → subject: `Charlie` |
| 6. "Let's" construction | Replace clitic `'s` subject with `team` | "Let's deploy" → subject: `team` |
| 7. Null subject fallback | Use speaker when no subject found | "Just need the API keys" (Dev1) → subject: `Dev1` |
| 8. Resultative constructions | Handle `have/get/make X ready` | "I'll have the prototype ready" → obj: `prototype` |
| 9. Triplet confidence scoring | Quality flags for downstream filtering | missing subject/object, pronoun subject, weak verb → lower score |

**Change in v2.0:** Fix #5 (`resolve_you_subject`) previously compared against a hardcoded set `{"PM", "Dev1", "Dev2", "QA", "Designer", "Everyone"}`. This **never matched** real transcript speaker names like "Alice", "Bob", "Charlie". The function now accepts a `known_speakers` parameter populated from the actual transcript, and falls back to the hardcoded set only if none is provided.

---

### 3.6 Sentence Type Flagging

**Module:** `pipeline/preprocessing/cleaner.py` (`flag_sentence_types`)

Each sentence is tagged with a semantic type used to calibrate detection confidence:

| Type | Description | Detection Confidence Prior |
|------|-------------|---------------------------|
| `general` | Default — could be a task | 0.70 |
| `observation` | Status/description (e.g., "Revenue is up 5%") | 0.20 |
| `consequence` | Reaction/outcome (e.g., "The board will be happy") | 0.25 |
| `metric` | Pure data (e.g., "Churn went from 3% to 5%") | 0.15 |

Detection is pattern-based using regex. Sentences matched as `observation`, `consequence`, or `metric` have their transformer confidence multiplied by the prior, heavily suppressing false positives from status-meeting content.

---

### 3.7 Meeting Type Detection

**Module:** `pipeline/detection/enhanced_features.py` (`detect_meeting_type`)

The full sentence list is scored against two signal sets:

- **Task-oriented signals:** `will`, `shall`, `need to`, `by friday`, `assign`, `action item`, `must`, `should`, …
- **Status meeting signals:** `numbers`, `revenue`, `growth`, `churn`, `metrics`, `percent`, `compared to`, `went from`, `is up`, …

The meeting type is determined by relative signal density:

| Condition | Type |
|-----------|------|
| Status signals > Task signals × 1.5 | `status_review` |
| Task signals > Status signals | `task_oriented` |
| Otherwise | `mixed` |

The detected type feeds into Stage 2 (confidence priors) and Stage 4 (validation thresholds).

---

## 4. Stage 2 — Decision Detection

**Module:** `pipeline/detection/`

Detection uses a three-component hybrid approach. All three run on every sentence; their outputs are fused before a final decision is made.

### 4.1 Rule-Based Pre-filter

**Module:** `pipeline/detection/rule_based.py`

A lightweight first pass that runs before any neural model. A sentence passes if and only if:
- It contains ≥ 4 words
- It is not matched by a non-actionable pattern (greetings, confirmations, facilitation phrases, pure observations)
- It contains at least one **action verb** from a curated vocabulary (~40 verbs including `deploy`, `review`, `schedule`, `configure`, `implement`, `fix`, `prepare`, etc.)

If the rule-based detector accepts a sentence, it marks `is_decision=True` with confidence `1.0`. This allows the pipeline to proceed even if the transformer is disabled (for debugging or speed).

---

### 4.2 Hard Filters

**Module:** `pipeline/detection/enhanced_features.py` (`DependencyFeatureAnalyzer.hard_filter`)

Before transformer inference, a second rule layer permanently rejects sentences that should **never** be tasks, regardless of what the transformer says:

- Generic single-word confirmations (`Good`, `Great`, `Agreed`)
- Reaction phrases (`That's great`, `That's concerning`)
- Closing meta-statements (`Anything else`, `I think that covers it`)
- Pure metric statements (`Revenue is up 5% compared to last quarter`)
- Past observations (`switched to a competitor`, `really helped drive signups`)

Hard-filtered sentences skip transformer scoring entirely and receive `confidence=0.1`.

**Design choice:** Running rule-based hard filters *before* the 330M-parameter transformer avoids unnecessary inference on sentences that have no chance of being valid tasks, improving throughput significantly.

---

### 4.3 Transformer-Based Classification (NLI)

**Module:** `pipeline/detection/classifier.py`

The core classifier uses `cross-encoder/nli-distilroberta-base` (a Natural Language Inference model) in a **zero-shot** classification setup. Each sentence is scored against three hypotheses:

```
H1: "This text is a decision made in the meeting."     → type: decision
H2: "This text is a person committing to a future action." → type: commitment
H3: "This text is general discussion or opinion."      → type: discussion
```

The model scores entailment probability for each hypothesis. Scores are normalised to sum to 1, producing a calibrated distribution. The label with the highest score is selected. Only `decision` and `commitment` types proceed downstream.

**Design choice:** Zero-shot NLI was chosen over a fine-tuned binary classifier because:
1. No labelled training data is required
2. The hypothesis text can be updated without retraining
3. NLI models are well-calibrated for entailment probability

A three-way classification (decision vs commitment vs discussion) produces better-separated confidence scores than binary classification because the model has an explicit "not a task" class to distribute probability mass to.

---

### 4.4 Feature Fusion

**Module:** `pipeline/detection/enhanced_features.py` (`EnhancedTransformerClassifier`)

The raw NLI confidence score is adjusted by three feature-derived factors:

**1. Modal boost** — If the sentence contains a deontic modal verb, its strength score is added as a confidence bonus:

| Modal | Strength |
|---|---|
| `must` | 1.00 |
| `need to`, `have to` | 0.95 |
| `should`, `shall` | 0.85 |
| `will`, `let's` | 0.80 |
| `would` | 0.70 |
| `can`, `may`, `could` | 0.40–0.50 |
| `might` | 0.30 |

A +0.10 bonus is added if the modal verb has a direct object (a more complete commitment structure).

**2. Downward prior** — Applied when commitment signals are weak. Sentence-type priors (observation=0.2, metric=0.15, general=0.7) multiply the base confidence. A suggestion/opinion marker (e.g., `maybe`, `I think`, `in my opinion`) triggers a hard 0.5 prior. Status meeting context applies an additional 0.7× multiplier.

**3. Tense prior** — Past tense (verb tags `VBD`/`VBN`) → 0.2× (completed work, not a new task). Present progressive (`VBG`) → 0.3× (ongoing status, not a new commitment). Future → 1.0×.

**4. Negation penalty** — Detected negation (`not`, `won't`, `can't`, `never`, etc.) → confidence set to 0.1. Negated commitments are not real commitments.

**Fusion formula:**

```
fused = (base_score × type_prior × tense_prior) + (modal_boost × 0.3)
```

If context window is enabled (default on, window=2), the prior two sentences are prepended as `[SEP]`-separated context:

```
final = fused × 0.6 + context_score × 0.4
```

**Three-zone confidence thresholds:**

| Zone | Range | Treatment |
|------|-------|-----------|
| HIGH | ≥ 0.70 | Auto-accept as decision |
| REVIEW | 0.40–0.70 | Accept, flag `requires_manual_review=True` |
| LOW | < 0.40 | Auto-reject |

---

### 4.5 Turn-Pair Acceptance Detector

**Module:** `pipeline/detection/hybrid_detector.py` (`detect_turn_pair_acceptances`)

After the main detection pass, the pipeline scans consecutive sentence pairs for request-acceptance patterns. If sentence N is a request/question and sentence N+1 is an acceptance, sentence N+1 is marked as a decision with `is_turn_pair_acceptance=True` and its confidence is boosted to 0.85.

This captures implicit commitments like:
```
Alice: Can you handle the load test? [request]
Bob: Sure, I can do that. [acceptance → marked as decision]
```

---

## 5. Stage 3 — Metadata Extraction

### 5.1 Assignee Extraction

**Module:** `pipeline/extraction/assignee.py`

Assignee extraction uses a **rule-first** strategy with a QA model as fallback:

**Priority 1 — Self-commitment:** If the sentence's resolved subject is `"I"` or `"me"`, the assignee is the current speaker. This covers the most common case: "I will handle this by Friday" → Bob.

**Priority 2 — Named addressee:** If the first 1–3 tokens contain a known speaker name (from the transcript's speaker set), that person is the assignee. Covers imperative directives: "Charlie, can you write the tests?" → Charlie.

**Priority 3 — Team commitment:** If the subject is `we`, `team`, `everyone`, or `all`, the assignee is `"team"`.

**Priority 4 — In-text reference:** Any known speaker name found anywhere in the sentence text is returned. Covers third-person references: "The DevOps lead should check the load balancer."

**Priority 5 — QA model fallback:** If no rule matches, a `deepset/roberta-base-squad2` QA model is invoked with the question `"Who will do this?"` over the sentence context. This is the only stage where the expensive QA model is used.

**Priority 6 — Default to speaker:** If all else fails, the sentence's speaker is returned as a default.

**Change in v2.0:** The `_known_speakers` set is now dynamically populated from the actual transcript speakers (passed from Stage 1) rather than being an empty set by default. This significantly improves Priority 2 and 4 matching.

---

### 5.2 Deadline Extraction

**Module:** `pipeline/extraction/deadline.py`

Deadline extraction uses two complementary methods:

**Primary — spaCy NER:** The `en_core_web_sm` model's named entity recognition is applied. Entities with label `DATE` or `TIME` are accepted if they pass a validity filter.

**Fallback — Regex matching:** A comprehensive set of 9 pre-compiled patterns covers:
- Day references: `by Friday`, `by next Monday`, `end of week`
- Month references: `by March 15`, `end of Q3`
- ISO dates: `2025-12-31`
- Slash dates: `12/31`
- Relative: `tomorrow`, `today`

A validity filter rejects false positives:
- Pure time-of-day strings (`morning`, `afternoon`)
- Past-tense time references (`last week`, `previously`, `ago`)
- Overly generic strings like `the task week`

**Change in v2.0:** The regex pattern list was a list of strings and was re-compiled into `re.Pattern` objects on every call to `_regex_extract`. Patterns are now compiled once at module load time. Additionally, the extractor now reuses the spaCy model instance from `sentence_splitter.py` (via `load_nlp_model()`) rather than loading a second `en_core_web_sm` process, reducing memory overhead.

---

## 6. Stage 4 — Postprocessing

### 6.1 Task Title Generation

**Module:** `pipeline/postprocessing/task_builder.py`

The goal is to produce a clean, imperative-style task title from raw conversational text. Two strategies are tried in order:

**Strategy 1 — Triplet-based title:** If the sentence has a `root_verb` and optionally an `object` from Stage 1, a title is composed directly:

```
root_verb="deploy" + object="the API" → "Deploy The API."
```

A `VERB_IMPERATIVES` map converts verb lemmas to their canonical imperative forms (e.g., `look` → `Investigate`, `revisit` → `Revisit`, `keep` → `Continue monitoring`). Titles are validated before use — rejected if they are a single word, contain only pronouns as objects, or use weak verbs (be, have, do) without a meaningful object.

**Strategy 2 — FLAN-T5 generation:** If triplet-based generation fails validation, `google/flan-t5-base` is prompted:

```
Convert the following meeting discussion into one short action item.
Remove names, pronouns, and conversational language.
Start with an imperative verb. Output only one sentence.

Discussion:
{text}

Action item:
```

The generated output is then validated against an action verb vocabulary and minimum word count. If it fails, the rule-based cleaner is used as the final fallback.

**Strategy 3 — Rule-based cleaning:** As a last resort, conversational prefixes (`I think`, `We should`, `I will`, `I'm going to`) and filler words (`just`, `actually`, `basically`) are stripped, the sentence is capitalised, and a period is appended.

---

### 6.2 Confidence Scoring

**Module:** `pipeline/postprocessing/confidence.py`

A composite confidence score replaces the raw detection score, incorporating extraction quality:

```
composite = (detection_conf × 0.50)
           + (extraction_completeness × 0.20)
           + (assignment_confidence × 0.15)
           + (deadline_confidence × 0.15)
```

| Component | Present | Absent |
|---|---|---|
| extraction_completeness | 0.75 | 0.50 |
| assignment_confidence | 1.00 | 0.50 |
| deadline_confidence | 1.00 | 0.60 |

**Change in v2.0:** The scorer previously looked up `task.get("detection_confidence", 1.0)`, but no upstream code ever set this key. Every task therefore received `detection_confidence=1.0`, nullifying the detection-stage confidence. The fix uses `task.get("confidence")` — the field that is actually set during Stage 2 — as the detection confidence input.

---

### 6.3 Task Validation

**Module:** `pipeline/postprocessing/task_validator.py`

A final filter pass removes remaining false positives that passed detection:

**Rejection rules:**
- Composite confidence < 0.50
- Marked `hard_filtered=True` during detection
- Matches known invalid patterns (metric statements, reactions, exclamations)
- **Meeting scheduling/facilitation** (added in v2.0): `meet again`, `schedule a follow-up`, `let's meet`, `wrap up`, `review progress`

**Stricter thresholds for weaker signal types:**
- Status review meeting type → confidence threshold raised to 0.65
- Sentence type is `observation`, `consequence`, or `metric` → threshold raised to 0.75

Tasks with confidence between 0.50 and 0.70 are not rejected but are flagged `requires_manual_review=True` in the output.

**Change in v2.0:** Added meeting-scheduling patterns to `INVALID_TASK_PATTERNS`. Previously, sentences like "Let's meet again on Friday to review progress" were being converted into tasks like "Meet Progress." which are not action items.

---

### 6.4 Deduplication

**Module:** `pipeline/postprocessing/deduplication.py`

Deduplication runs in two passes:

**Pass 1 — Exact match:** Case-insensitive title comparison. Exact duplicates are collapsed, keeping the highest-confidence version.

**Pass 2 — Semantic similarity:** Remaining tasks are embedded using `all-mpnet-base-v2` (sentence-transformers). Cosine similarity is computed between every pair of remaining tasks. Tasks with similarity ≥ 0.80 are merged, keeping the highest-confidence version.

If `sentence-transformers` is not available, a `difflib.SequenceMatcher` string similarity fallback is used.

**Design choice:** Two-pass deduplication is necessary because exact match misses rephrased but semantically equivalent tasks. For example:
- "finish OAuth integration by tomorrow"
- "complete the OAuth work tomorrow"

These resolve to the same semantic embedding and are correctly merged into one task (keeping whichever has higher confidence).

---

## 7. Design Choices & Rationale

### Why Zero-Shot NLI Over a Fine-Tuned Classifier?

A fine-tuned binary classifier would perform better on a specific labelled dataset, but requires labelled training data, retraining when domain shifts, and is less interpretable. The NLI approach uses `cross-encoder/nli-distilroberta-base` as a general entailment engine pointed at human-readable hypotheses. The hypothesis text can be changed without any model updates, making it easy to tune the semantics of "what a task is" for different meeting contexts.

### Why Rule-Based Assignee Extraction First?

QA models are expensive (sequential inference, 490MB weights) and often overfit to named entity spans. For the most common cases (self-commitments, named addressees in imperatives, team commitments), deterministic rules are faster and more reliable. The QA model is reserved for truly ambiguous cases where rules produce no match.

### Why Triplet-Based Title Generation Over LLM-Only?

Generating every title via FLAN-T5 is slow (one forward pass per sentence, sequential). Triplet-based generation using parsed `root_verb + object` is deterministic, instant, and produces grammatically predictable output. FLAN-T5 is only invoked when the dependency parse did not produce a usable triplet, serving as a smart fallback rather than the default path.

### Why Context Window for Detection?

Meeting discourse is highly anaphoric. A sentence like "I'll take care of that" is only identifiable as a task if the prior context ("Can you deploy the API by Friday?") is known. The context window (last 2 sentences prepended with `[SEP]`) provides the minimal discourse context needed for the classifier to resolve inter-sentential commitments.

### Why Meeting Type Detection?

Status review meetings (e.g., quarterly business reviews) produce many declarative sentences with modal-adjacent language ("revenue is up", "we should see better numbers") that confuse the classifier. By detecting meeting type early, the confidence priors in Stage 2 can be tuned accordingly, reducing false positives in status meetings without affecting task-oriented meeting recall.

---

## 8. Changes Made in v2.0

The following changes were made during the April 2026 code review:

| Area | File | Change |
|------|------|--------|
| **Bug — Broken export** | `preprocessing/__init__.py` | Removed `post_process_metadata` (does not exist); added real exports `resolve_triplets`, `flag_sentence_types` |
| **Bug — Duplicate constants** | `postprocessing/task_builder.py` | Removed first of two identical constant definition blocks (30 lines). The second, correct block with proper contraction patterns (`i'?m`, `we'?ll`) was retained |
| **Bug — Filler regex** | `preprocessing/cleaner.py` | Fixed regex that removed "like" from valid prepositional phrases ("tools like Kubernetes"). Now only removes filler "like" |
| **Bug — Dead code** | `run_pipeline.py` | Removed duplicate `if not decision_sentences` guard (lines 186–188 were identical to 182–184) |
| **Bug — Inefficient re-call** | `run_pipeline.py` | Removed redundant `split_sentences(speaker_utterances)` call used only for logging (loaded spaCy again) |
| **Logic — Detection confidence** | `postprocessing/confidence.py` | Fixed scorer to use `task["confidence"]` (actual detection score) instead of `task["detection_confidence"]` (never set, always defaulted to 1.0) |
| **Logic — Hardcoded speakers** | `preprocessing/triplet_resolver.py` | Made `KNOWN_SPEAKERS` dynamic; `resolve_triplets()` now accepts `known_speakers` from the actual transcript |
| **Logic — Sync entry point** | `run_pipeline.py` | Synced with `pipeline.py`: added `flag_sentence_types`, `detect_meeting_type`, speaker extraction, `AssigneeExtractor.set_known_speakers()`, `meeting_type` to `detect_batch()`, `root_verb`/`object`/`sentence_type` in task definitions, `TaskValidator` calls |
| **Logic — Scheduling filter** | `postprocessing/task_validator.py` | Added patterns for meeting-scheduling statements (e.g., `meet again`, `review progress`) to `INVALID_TASK_PATTERNS` |
| **Performance — Regex compile** | `extraction/deadline.py` | Moved regex `compile()` calls from inside `_regex_extract()` to module load time |
| **Performance — spaCy model** | `extraction/deadline.py` | Reuses spaCy model loaded by `sentence_splitter` instead of loading a second `en_core_web_sm` instance |

---

## 9. Known Limitations & Future Work

### Current Limitations

- **No coreference beyond same-speaker anaphora:** The anaphora resolver only carries objects forward per-speaker. Cross-speaker coreference ("Do the thing Bob mentioned → `thing` = API refactor) is not resolved.
- **Single-sentence scope:** Each sentence is classified independently (with a 2-sentence lookback window only). Multi-sentence action items are not handled.
- **No temporal normalisation:** Deadlines are extracted as raw text strings ("by next Friday", "end of Q3") but not resolved to absolute dates.
- **Classifier runs sentence-by-sentence:** The NLI classifier runs one sentence at a time. True batching (padding all sentences to the same length and running a single forward pass) is not yet implemented, which limits throughput on longer transcripts.
- **FLAN-T5 title quality:** For very short or telegraphic sentences, the FLAN-T5 prompt sometimes generates titles that are too generic. The triplet fallback is preferred when available.

### Planned Improvements

- True batch inference for the NLI classifier
- Deadline normalisation to absolute datetime using `dateparser`
- Cross-speaker coreference resolution
- Fine-tuned classification head on labelled meeting data (AMI, ICSI corpora)
- Priority/urgency extraction alongside assignee and deadline
