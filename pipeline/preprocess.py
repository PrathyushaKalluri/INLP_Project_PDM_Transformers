"""
Transcript Preprocessing Module
Converts raw meeting transcripts into structured sentence-level dataset
for downstream NLP components (decision detection, clustering, summarization).
"""

import json
import spacy
from pathlib import Path


def preprocess_transcript(transcript: str) -> list:
    """
    Convert raw meeting transcript into structured sentence-level dataset.
    
    Args:
        transcript (str): Raw meeting transcript text with format:
                         "Speaker: utterance"
    
    Returns:
        list: List of dictionaries with keys:
              - sentence_id (int): Sequential identifier
              - speaker (str): Speaker name
              - text (str): Cleaned sentence text
    
    Example:
        >>> transcript = "A: we should deploy tomorrow\\nB: yes let's finalize the pricing"
        >>> result = preprocess_transcript(transcript)
        >>> print(result[0])
        {'sentence_id': 1, 'speaker': 'A', 'text': 'we should deploy tomorrow'}
    """
    
    # Load spaCy English model
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        raise OSError(
            "spaCy model 'en_core_web_sm' not found. "
            "Install it with: python -m spacy download en_core_web_sm"
        )
    
    sentences = []
    sentence_id = 1
    
    # Split transcript into lines
    lines = transcript.strip().split('\n')
    
    for line in lines:
        # Skip blank lines
        line = line.strip()
        if not line:
            continue
        
        # Extract speaker and text using ":" delimiter
        if ':' not in line:
            continue
        
        speaker, text = line.split(':', 1)
        speaker = speaker.strip()
        text = text.strip()
        
        # Skip if speaker or text is empty
        if not speaker or not text:
            continue
        
        # Use spaCy for sentence segmentation
        doc = nlp(text)
        
        # Extract sentences from spaCy Doc object
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Skip empty sentences
            if sent_text:
                sentences.append({
                    "sentence_id": sentence_id,
                    "speaker": speaker,
                    "text": sent_text
                })
                sentence_id += 1
    
    return sentences


def save_processed_transcript(sentences: list, output_path: str) -> None:
    """
    Save structured sentences to JSON file.
    
    Args:
        sentences (list): List of sentence dictionaries
        output_path (str): Path to output JSON file
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(sentences, f, indent=2)
    
    print(f"✓ Processed transcript saved to: {output_path}")
    print(f"✓ Total sentences: {len(sentences)}")


def load_raw_transcript(input_path: str) -> str:
    """
    Load raw transcript from file.
    
    Args:
        input_path (str): Path to raw transcript file
    
    Returns:
        str: Raw transcript text
    """
    with open(input_path, 'r') as f:
        return f.read()


if __name__ == "__main__":
    # Example usage
    example_transcript = """A: we should deploy the payment API tomorrow
B: yeah let's finalize the pricing model
C: okay I will send the report by evening"""
    
    print("Processing example transcript...")
    result = preprocess_transcript(example_transcript)
    
    print("\nStructured output:")
    for sentence in result:
        print(f"  {sentence}")
    
    # Save to file
    output_file = "data/processed_transcripts/meeting1.json"
    save_processed_transcript(result, output_file)
