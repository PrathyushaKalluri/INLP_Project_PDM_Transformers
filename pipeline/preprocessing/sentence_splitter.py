"""Split utterances into sentences using spaCy with metadata enrichment."""

import spacy
from typing import List, Dict


def load_nlp_model():
    """Load spaCy English model."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        raise OSError(
            "spaCy model 'en_core_web_sm' not found. "
            "Install it with: python -m spacy download en_core_web_sm"
        )


def _extract_metadata(spacy_sent):
    """
    Extract linguistic metadata from a spaCy sentence with improved handling.
    
    Improvements:
    - Root verb resolution: Handle modals/auxiliaries (go, have, let)
    - Object extraction: Capture dobj, attr, pobj (prepositional objects)
    - Subject extraction: Detect imperative subjects from addressees
    
    Returns:
        dict: Contains root_verb, object (noun phrase), subject
    """
    metadata = {
        "root_verb": None,
        "object": None,
        "subject": None,
    }
    
    try:
        # ── 1. FIND ROOT VERB (with modal/auxiliary resolution) ──────────
        root_token = None
        for token in spacy_sent:
            if token.dep_ == "ROOT":
                root_token = token
                break
        
        if root_token:
            # Check if root is modal/auxiliary - walk down to find main verb
            if root_token.pos_ in ("VERB", "AUX"):
                # If it's a modal or auxiliary, find the first non-auxiliary child verb
                actual_verb = root_token
                if root_token.lemma_ in ("go", "have", "let", "be", "will", "would", 
                                         "could", "should", "may", "might", "must", "can"):
                    # Look for child verbs
                    for child in root_token.children:
                        if child.pos_ == "VERB" and child.dep_ in ("xcomp", "ccomp", "advcl"):
                            actual_verb = child
                            break
                
                metadata["root_verb"] = actual_verb.lemma_
        
        # ── 2. FIND SUBJECT (including imperative subjects) ──────────────
        subject_token = None
        
        # First try explicit subject
        for token in spacy_sent:
            if token.dep_ in ("nsubj", "nsubjpass"):
                subject_token = token
                break
        
        # If no explicit subject, check for imperative with addressee
        if not subject_token:
            tokens_list = list(spacy_sent)
            
            # Pattern 1: npadvmod (noun phrase adverbial modifier) - addressee in imperatives
            # e.g., "Everyone, please review..." → "Everyone" is npadvmod
            for token in tokens_list:
                if token.dep_ == "npadvmod":
                    subject_token = token
                    break
            
            # Pattern 2: Noun/Proper noun before comma (e.g., "John, please...")
            if not subject_token:
                for i, token in enumerate(tokens_list):
                    if token.text == "," and i > 0:
                        prev_token = tokens_list[i - 1]
                        if prev_token.pos_ in ("NOUN", "PROPN") or prev_token.ent_type_ in ("PERSON", "ORG"):
                            subject_token = prev_token
                            break
            
            # Pattern 3: First proper noun at beginning if no explicit subject (imperative)
            if not subject_token:
                for token in tokens_list:
                    if token.pos_ in ("PROPN",) and token != root_token:
                        # Check if it comes before the verb
                        if root_token and token.i < root_token.i:
                            subject_token = token
                            break
        
        if subject_token:
            # Collect compound subjects
            subject_tokens = [subject_token.text]
            for child in subject_token.children:
                if child.dep_ in ("compound", "amod"):
                    subject_tokens.insert(0, child.text)
            metadata["subject"] = " ".join(subject_tokens)
        
        # ── 3. FIND OBJECT (dobj, attr, pobj) ───────────────────────────
        # Priority: dobj/obj (prefer nouns over pronouns) > attr > pobj
        # IMPROVED: Skip temporal modifiers, handle "have X ready" patterns
        # Strategy: Collect all candidates, then select best one
        
        candidates = []  # List of (priority, is_pronoun, text)
        
        priority_map = {
            "dobj": 1,      # Direct object (highest priority)
            "obj": 1,
            "iobj": 2,      # Indirect object
            "attr": 3,      # Attribute (e.g., "be ready")
            "pobj": 4,      # Prepositional object (lowest)
        }
        
        for token in spacy_sent:
            if token.dep_ in priority_map:
                priority = priority_map[token.dep_]
                
                # SKIP: Temporal modifiers (pobj after by/at/in/before/after/during/over/upon/throughout)
                if token.dep_ == "pobj":
                    # Check if parent preposition is temporal
                    parent = token.head
                    if parent.lemma_ in ("by", "at", "in", "before", "after", "during", "over", "upon", "throughout"):
                        continue
                
                # Collect compound nouns/adjectives and determiners
                obj_parts = []
                
                # Collect preceding modifiers (det, amod, compound)
                for child in sorted(token.children, key=lambda t: t.i):
                    if child.dep_ in ("det", "amod", "compound"):
                        obj_parts.append(child.text)
                
                # Add main token
                obj_parts.append(token.text)
                
                # Collect following modifiers (but not purpose clauses)
                for child in sorted(token.children, key=lambda t: t.i):
                    if child.dep_ not in ("det", "amod", "compound") and child.dep_ != "acl":
                        if child.pos_ in ("NOUN", "ADJ") and child.dep_ in ("compound", "prep"):
                            obj_parts.append(child.text)
                
                obj_text = " ".join(obj_parts)
                is_pronoun = token.pos_ == "PRON"
                candidates.append((priority, is_pronoun, obj_text))
        
        # Select best candidate: lowest priority, prefer non-pronouns at same priority
        best_object = None
        if candidates:
            # Sort by: (priority, is_pronoun) - so best is lowest priority and non-pronoun
            candidates.sort(key=lambda x: (x[0], x[1]))
            best_object = candidates[0][2]
        
        # ── SPECIAL: Handle resultative constructions ──────────────────────
        # "have X ready", "get X done", "make X ready" where X is the real object
        # Parse: "have" (ROOT) -> "ready" (ccomp) -> "prototype" (nsubj of ready)
        if root_token and root_token.lemma_ in ("have", "get", "make", "keep"):
            for child in root_token.children:
                # Look for ccomp or acomp (complement of manner/state)
                if child.dep_ in ("ccomp", "acomp"):
                    # Find nsubj of this complement - that's the real object
                    for grandchild in child.children:
                        if grandchild.dep_ == "nsubj":
                            obj_parts = []
                            for subchild in sorted(grandchild.children, key=lambda t: t.i):
                                if subchild.dep_ in ("det", "amod", "compound"):
                                    obj_parts.append(subchild.text)
                            obj_parts.append(grandchild.text)
                            best_object = " ".join(obj_parts)
                            break
        
        if best_object:
            metadata["object"] = best_object
    
    except Exception as e:
        pass  # If extraction fails, leave as None
    
    return metadata


def split_sentences(
    speaker_utterances: List[Dict],
) -> List[Dict]:
    """
    Split speaker utterances into sentence-level structured data with metadata.
    
    Args:
        speaker_utterances (List[Dict]): List of turn dictionaries with:
                                        - speaker (str)
                                        - text (str)
                                        - turn_id (int, optional)
                                        - timestamp (str, optional)
    
    Returns:
        List[Dict]: List of sentence dictionaries with keys:
                   - sentence_id (int)
                   - turn_id (int, optional)
                   - speaker (str)
                   - timestamp (str, optional)
                   - text (str)
                   - root_verb (str, optional): Main verb in sentence
                   - object (str, optional): Direct object noun phrase
                   - subject (str, optional): Subject of sentence
    """
    nlp = load_nlp_model()
    sentences = []
    sentence_id = 1
    
    for utterance in speaker_utterances:
        # Handle both old tuple format and new dict format
        if isinstance(utterance, tuple):
            speaker, text = utterance
            turn_id = None
            timestamp = None
        else:
            speaker = utterance.get("speaker", "unknown")
            text = utterance.get("text", "")
            turn_id = utterance.get("turn_id")
            timestamp = utterance.get("timestamp")
        
        if not text:
            continue
        
        doc = nlp(text)
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if sent_text:
                # Extract metadata once per sentence
                metadata = _extract_metadata(sent)
                
                # ── FIX: Default to speaker as subject if subject is null ──────
                # If subject is not found and sentence is not passive, use speaker
                if not metadata["subject"]:
                    # Check if sentence is passive (has nsubjpass or is passive construction)
                    is_passive = any(token.dep_ == "nsubjpass" for token in sent)
                    
                    # Use speaker as default subject if not passive
                    if not is_passive and speaker != "unknown":
                        metadata["subject"] = speaker
                
                sentence_dict = {
                    "sentence_id": sentence_id,
                    "speaker": speaker,
                    "text": sent_text,
                    "root_verb": metadata["root_verb"],
                    "object": metadata["object"],
                    "subject": metadata["subject"],
                    "spacy_doc": sent,  # Include spaCy doc for feature extraction (not serialized to JSON)
                }
                
                # Add optional fields if present
                if turn_id is not None:
                    sentence_dict["turn_id"] = turn_id
                if timestamp is not None:
                    sentence_dict["timestamp"] = timestamp
                
                sentences.append(sentence_dict)
                sentence_id += 1
    
    return sentences

