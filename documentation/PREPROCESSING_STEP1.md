# Pipeline Step 1: Transcript Preprocessing

## Overview

This module implements the first step of the NLP pipeline for automatic action item extraction from meeting transcripts.

**Input:** Raw meeting transcript with speaker labels
**Output:** Structured JSON with sentence-level metadata

## What It Does

✓ Loads raw meeting transcripts  
✓ Extracts speaker and utterance using ":" delimiter  
✓ Segments utterances into sentences using spaCy NLP  
✓ Assigns sequential sentence IDs  
✓ Preserves speaker information and conversation order  
✓ Handles edge cases (blank lines, extra spaces, multiple sentences per utterance)  
✓ Saves structured data as JSON  

## What It Does NOT Do

✗ Detect decision sentences (done in Step 2)  
✗ Cluster related decisions (done in Step 3)  
✗ Generate summaries (done in Step 4)  
✗ Extract action items (done in Step 5)  

This step **only structures the data** for downstream ML components.

## Installation

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Usage

### Basic Example

```python
from pipeline.preprocess import preprocess_transcript

transcript = """A: we should deploy the payment API tomorrow
B: yeah let's finalize the pricing model"""

sentences = preprocess_transcript(transcript)
print(sentences)
```

Output:
```json
[
  {
    "sentence_id": 1,
    "speaker": "A",
    "text": "we should deploy the payment API tomorrow"
  },
  {
    "sentence_id": 2,
    "speaker": "B",
    "text": "yeah let's finalize the pricing model"
  }
]
```

### Processing a File

```python
from pipeline.preprocess import load_raw_transcript, preprocess_transcript, save_processed_transcript

# Load from file
raw = load_raw_transcript("data/raw_transcripts/meeting1.txt")

# Process
sentences = preprocess_transcript(raw)

# Save to JSON
save_processed_transcript(sentences, "data/processed_transcripts/meeting1.json")
```

### Run Example

```bash
python example_usage.py
```

## Output Format

Each sentence object contains:

```json
{
  "sentence_id": 1,           // Sequential integer
  "speaker": "A",             // Speaker name (extracted before ":")
  "text": "utterance text"     // Cleaned, single sentence
}
```

## Input Format

Raw transcripts must follow the format:

```
Speaker_Name: utterance text
Another_Speaker: more text
```

Examples:
```
A: we should deploy tomorrow
John: let's finalize the design. I'll do it today.
Alice: I will prepare documentation.
```

## Example Output Snippet

From 10-speaker meeting processed example:

```json
[
  {"sentence_id": 1, "speaker": "A", "text": "good morning everyone."},
  {"sentence_id": 2, "speaker": "A", "text": "let's start with the Q1 planning"},
  {"sentence_id": 3, "speaker": "B", "text": "thanks for having us."},
  {"sentence_id": 4, "speaker": "B", "text": "I think we should focus on the payment API first"},
  {"sentence_id": 5, "speaker": "A", "text": "absolutely."},
  {"sentence_id": 6, "speaker": "A", "text": "we need to deploy it by end of march."},
  ...
]
```

## Edge Cases Handled

| Case | Input | Output |
|------|-------|--------|
| Multiple sentences | `A: deploy tomorrow. do it fast.` | Two separate sentence objects with same speaker |
| Extra spaces | `A:   message   ` | `"text": "message"` (stripped) |
| Blank lines | (empty lines between utterances) | Skipped |
| No punctuation | `A: we should do this` | Still segmented correctly by spaCy |
| Missing colon | `just random text` | Skipped (invalid format) |

## Data Structure Preparation

This preprocessing step prepares data for downstream components:

1. **Decision Detection** → Uses sentence_id and text
2. **Clustering** → Groups sentences by semantic similarity
3. **Summarization** → Generates concise summaries per cluster
4. **Task Extraction** → Links summaries to evidence sentences
5. **Board Display** → Shows tasks with clickable evidence links

## Technical Details

- **spaCy Model:** `en_core_web_sm` (trained on English web text)
- **Sentence Tokenization:** spaCy's dependency parser identifies sentence boundaries
- **Speaker Extraction:** Simple ":" delimiter splitting
- **Output Format:** JSON with 2-space indentation for readability

## Files

- `pipeline/preprocess.py` - Main preprocessing module
- `example_usage.py` - Example script demonstrating usage
- `data/raw_transcripts/` - Input directory for raw transcripts
- `data/processed_transcripts/` - Output directory for structured JSON

## Next Steps

Once transcripts are preprocessed, the pipeline continues:

1. ✅ **Step 1: Preprocessing** (this module)
2. 📋 Step 2: Decision Detection (rule-based or transformer)
3. 🔗 Step 3: Clustering (semantic similarity)
4. 📝 Step 4: Summarization (abstractive or extractive)
5. ✓ Step 5: Task Generation (from summaries)
6. 🎯 Step 6: Display on Board (with evidence linking)

## Performance Notes

- Processing 100 sentences typically takes <1-2 seconds
- spaCy model is loaded once and cached in memory
- JSON output scales linearly with number of sentences
- Suitable for real-time transcript processing in web app
