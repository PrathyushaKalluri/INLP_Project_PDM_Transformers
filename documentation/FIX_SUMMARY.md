# Fix Summary: Object Extraction with Temporal Modifiers

## Problem Identified

Sentence 34 was incorrectly extracting "the weekend" as the direct object instead of "that":
```
Sentence: "Let me handle that over the weekend."
Before Fix: Object = "the weekend" ❌
After Fix:  Object = "that" ✅
```

## Root Cause

The temporal modifier filter in [pipeline/preprocessing/sentence_splitter.py](pipeline/preprocessing/sentence_splitter.py) was incomplete. It was skipping prepositional objects (pobj) that appeared after temporal prepositions, but the list didn't include **"over"**.

The code was:
```python
if parent.lemma_ in ("by", "at", "in", "before", "after", "during"):
```

But "over the weekend" is a temporal phrase, and "over" wasn't in the list.

## Solution Implemented

### 1. Extended Temporal Prepositions List
Added "over", "upon", and "throughout" to the temporal preposition filter:

```python
if parent.lemma_ in ("by", "at", "in", "before", "after", "during", "over", "upon", "throughout"):
    continue
```

This ensures that "weekend" (a pobj after "over") is recognized as a temporal modifier and skipped.

### 2. Refactored Object Selection Logic  
Changed from a greedy selection approach to a candidate-based approach:

**Before:**
```python
for token in spacy_sent:
    # Greedily select best as we iterate
    if priority < best_priority or (priority == best_priority and token.pos_ != "PRON"):
        best_object = ...
```

**After:**
```python
candidates = []
for token in spacy_sent:
    # Collect all candidates
    candidates.append((priority, is_pronoun, obj_text))

# Sort: by priority, then prefer non-pronouns
candidates.sort(key=lambda x: (x[0], x[1]))
best_object = candidates[0][2]
```

This approach is more robust and prevents pronouns from being skipped too early before all options are evaluated.

## Verification

All temporal modifier cases now work correctly:

| Sentence | Temporal Phrase | Correct Object |
|----------|-----------------|-----------------|
| Let me handle **that** over the weekend | "over the weekend" | ✅ that |
| I can do **this** by Friday | "by Friday" | ✅ this |
| Release **it** during the sprint | "during the sprint" | ✅ it |
| Check **the system** tomorrow | temporal position | ✅ the system |

## Files Modified

- [pipeline/preprocessing/sentence_splitter.py](pipeline/preprocessing/sentence_splitter.py)
  - Lines 105-160: Updated object extraction logic
  - Line 122: Extended temporal prepositions list

## Testing

```python
from pipeline.preprocessing import split_sentences

result = split_sentences([{'speaker': 'PM', 'text': 'Let me handle that over the weekend.'}])
print(result[0]['object'])  # Output: "that" ✅
```
