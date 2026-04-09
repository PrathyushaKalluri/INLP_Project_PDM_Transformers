"""Text cleaning utilities including Indian English normalization."""

import re
from typing import Dict, List


# Patterns for observational sentences (status/metrics)
OBSERVATION_PATTERNS = [
    r"\b(is|are|was|were)\s+(up|down|good|bad|high|low)\b",
    r"(compared\s+to|went\s+from|helped\s+drive|switched\s+to)",
    r"\b(seems?|appears?|looks?)\s+(to\s+be|like)?\s*(good|fine|well|working)",
]

# Patterns for consequence/reaction statements
CONSEQUENCE_PATTERNS = [
    r"(will\s+be\s+happy|will\s+be\s+pleased|should\s+be\s+fine)",
    r"(that'?s\s+(great|good|concerning|interesting|valid))",
]

# Patterns for metric/data statements
METRIC_PATTERNS = [
    r"\d+\s*%",
    r"(revenue|conversion|churn|growth|retention)\s+(rate|is|was|went)",
]


# Indian English to Standard English mapping
INDIAN_ENGLISH_MAP = {
    "prepone": "move earlier",
    "do the needful": "take necessary action",
    "revert back": "reply",
    "kindly": "",
    "pls": "please",
    "pl": "please",
    "abt": "about",
    "asap": "as soon as possible",
    "tym": "time",
    "f2f": "face to face",
}


def normalize_indian_english(text: str) -> str:
    """
    Normalize Indian English phrases to standard English.
    
    Args:
        text (str): Text with potential Indian English phrases
    
    Returns:
        str: Normalized text
    """
    normalized = text
    
    for indian_phrase, standard_phrase in INDIAN_ENGLISH_MAP.items():
        # Case-insensitive replacement with word boundaries
        pattern = r'\b' + re.escape(indian_phrase) + r'\b'
        normalized = re.sub(pattern, standard_phrase, normalized, flags=re.IGNORECASE)
    
    return normalized


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text (str): Raw text to clean
    
    Returns:
        str: Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common filler words patterns
    text = re.sub(r'\bum\b|\buh\b|\blike\b(?!\s+\w+ing)', ' ', text, flags=re.I)
    
    # Apply Indian English normalization
    text = normalize_indian_english(text)
    
    # Collapse any resulting extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text.strip()


def clean_sentences(sentences: List[Dict]) -> List[Dict]:
    """
    Apply text cleaning to all sentences.
    
    Args:
        sentences (List[Dict]): List of sentence dictionaries
    
    Returns:
        List[Dict]: Cleaned sentence dictionaries
    """
    cleaned = []
    for sent in sentences:
        sent_copy = sent.copy()
        sent_copy["text"] = clean_text(sent["text"])
        if sent_copy["text"]:  # Skip if cleaning resulted in empty string
            cleaned.append(sent_copy)
    
    return cleaned


def flag_sentence_type(sent: Dict) -> Dict:
    """
    Classify sentence semantic type (observation, consequence, metric, or general).
    
    This flags sentences that are less likely to be actionable tasks:
    - observation: Status/description (e.g., "Revenue is up 5%")
    - consequence: Reaction/outcome (e.g., "That's great")
    - metric: Pure data/numbers (e.g., "Churn went from 3% to 5%")
    - general: Normal statement that could be a task
    
    Args:
        sent (Dict): Sentence dictionary with 'text' key
    
    Returns:
        Dict: Sentence with added 'sentence_type' field
    """
    text = sent.get("text", "").lower()
    sent_copy = sent.copy()
    
    # Check in order of specificity (most specific first)
    if any(re.search(p, text) for p in METRIC_PATTERNS):
        sent_copy["sentence_type"] = "metric"
    elif any(re.search(p, text) for p in OBSERVATION_PATTERNS):
        sent_copy["sentence_type"] = "observation"
    elif any(re.search(p, text) for p in CONSEQUENCE_PATTERNS):
        sent_copy["sentence_type"] = "consequence"
    else:
        sent_copy["sentence_type"] = "general"
    
    return sent_copy


def flag_sentence_types(sentences: List[Dict]) -> List[Dict]:
    """
    Flag semantic type for all sentences.
    
    Args:
        sentences (List[Dict]): List of sentence dictionaries
    
    Returns:
        List[Dict]: Sentences with 'sentence_type' field added
    """
    return [flag_sentence_type(sent) for sent in sentences]

