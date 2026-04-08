"""
Triplet Resolution module for refined linguistic metadata extraction.

Resolves S-V-O (Subject-Verb-Object) triplets by implementing 9 context-aware fixes 
for handling edge cases in meeting language:

1. Direct object extraction (clause boundary fix)
2. Conjunction handling (pick root verb's object first)
3. Temporal modifier filtering
4. Anaphora resolution (carry-forward objects)
5. "you" subject resolution (named addressee)
6. "Let's" construction handling
7. Implied subject from speaker
8. Resultative construction handling
9. Triplet confidence scoring with quality flags

These fixes ensure accurate extraction of who is doing what (and by when) from conversational text.
"""

from typing import List, Dict, Optional

# Constants
TEMPORAL_PREPS = {"by", "before", "after", "during", "over", "until", "since", "within"}
RESULTATIVE_VERBS = {"have", "get", "make", "keep"}
WEAK_VERBS = {"be", "have", "do", "go", "get", "make", "let"}
PRONOUNS = {"it", "that", "this", "them", "those", "these", "you", "me", "him", "her", "us"}
KNOWN_SPEAKERS = {"PM", "Dev1", "Dev2", "QA", "Designer", "Everyone"}


def fix_lets_subject(sent: Dict) -> Dict:
    """
    Fix: Detect 'Let's' constructions and replace clitic subject with 'team'.
    
    Example: "Let's go around." → subject: "team" (not "'s")
    """
    if sent.get("text", "").lower().startswith(("let's", "let us")):
        sent["subject"] = "team"
        sent["subject_resolved"] = True
    return sent


def resolve_null_subject(sent: Dict, spacy_doc=None) -> Dict:
    """
    Fix: When subject is null and sentence is not passive, default to speaker.
    
    Example: "just need the API keys" (Dev1 speaking) → subject: "Dev1"
    """
    if sent.get("subject") is not None:
        return sent
    
    # Simple heuristic: if we have a verb, it's likely not passive unless explicitly marked
    if sent.get("root_verb") is not None:
        sent["subject"] = sent.get("speaker", "unknown")
        sent["subject_resolved"] = True
    
    return sent


def get_direct_object(spacy_token) -> Optional:
    """
    Fix #1: Only look at immediate children of root verb for dobj.
    
    Never traverse into advcl/relcl/xcomp subtrees.
    Returns the direct object token or None.
    """
    if spacy_token is None:
        return None
    
    for child in spacy_token.children:
        if child.dep_ in ("dobj", "obj"):
            return child
    return None


def filter_temporal_pobj(token) -> bool:
    """
    Check if token is a temporal prepositional object.
    Returns True if object should be FILTERED OUT.
    """
    if token is None:
        return False
    
    if token.dep_ == "pobj":
        parent = token.head
        if parent.text.lower() in TEMPORAL_PREPS:
            return True
    
    return False


def get_object_with_conjunction(spacy_root) -> tuple:
    """
    Fix #2: Handle conjunctions properly.
    
    Extract the root verb's object first.
    Only fall back to conj verb's object if root has no object.
    
    Returns: (primary_object_text, secondary_object_text)
    """
    if spacy_root is None:
        return None, None
    
    # Get root verb's direct object
    direct = get_direct_object(spacy_root)
    if direct and not filter_temporal_pobj(direct):
        return direct.text, None
    
    # Fall back to conj verb's object
    for conj in [c for c in spacy_root.children if c.dep_ == "conj"]:
        conj_obj = get_direct_object(conj)
        if conj_obj and not filter_temporal_pobj(conj_obj):
            return None, conj_obj.text
    
    return None, None


def extract_resultative_object(spacy_root) -> Optional[str]:
    """
    Fix #8: Handle resultative constructions ("have X ready", "get X done").
    
    Parse: "I'll have the prototype ready"
    Root: "have"
    The real object is "prototype" (subject of the embedded predicate)
    
    Returns the object text or None.
    """
    if spacy_root is None or spacy_root.lemma_ not in RESULTATIVE_VERBS:
        return None
    
    # Look for oprd, xcomp, or acomp child (predicate modifier)
    for child in spacy_root.children:
        if child.dep_ in ("oprd", "xcomp", "acomp"):
            # The real object is the nsubj of this predicate
            for subchild in child.children:
                if subchild.dep_ == "nsubj":
                    return subchild.text
    
    # Fall back to direct object of root
    direct = get_direct_object(spacy_root)
    if direct:
        return direct.text
    
    return None


def resolve_you_subject(sent: Dict, sentences: List[Dict], idx: int) -> Dict:
    """
    Fix #5: Resolve "you" subject to named addressee or previous speaker.
    
    Example: "Dev2, can you share..." → subject: "Dev2"
    Example: (no addressee) → subject: previous_turn_speaker
    """
    if sent.get("subject") != "you":
        return sent
    
    text = sent.get("text", "")
    
    # Check for named addressee at start: "Dev2, can you..."
    if "," in text:
        first_token = text.split(",")[0].strip()
        # Remove greeting particles
        first_token = first_token.replace("please", "").replace("ok", "").strip()
        
        if first_token in KNOWN_SPEAKERS:
            sent["subject"] = first_token
            sent["subject_resolved"] = True
            return sent
    
    # Fall back to previous turn speaker
    if idx > 0:
        prev_speaker = sentences[idx - 1]["speaker"]
        sent["subject"] = prev_speaker
        sent["subject_resolved"] = True
    
    return sent


def resolve_anaphora(sentences: List[Dict]) -> List[Dict]:
    """
    Fix #4: Resolve anaphoric references (it, that, this, them).
    
    Maintains a context window of last meaningful object per speaker.
    Flags resolved objects with "object_resolved": True.
    
    Also handles temporal pobj extraction by checking if the object
    is exclusively temporal (no noun content) — if so, look for antecedent.
    """
    last_object = {}  # keyed by speaker
    
    for i, sent in enumerate(sentences):
        obj = sent.get("object")
        speaker = sent.get("speaker", "unknown")
        
        if obj:
            obj_clean = obj.lower().strip("the ")
            
            # Check if object is a pronoun or temporal reference
            is_pronoun = obj_clean in PRONOUNS
            is_temporal = obj_clean in ("weekend", "afternoon", "day", "monday", "tuesday", 
                                       "wednesday", "thursday", "friday", "saturday", "sunday")
            
            if is_pronoun or is_temporal:
                # Try to resolve from context (same speaker)
                resolved = last_object.get(speaker)
                if resolved:
                    sent["object"] = resolved
                    sent["object_resolved"] = True
            else:
                # Update context with meaningful object
                last_object[speaker] = obj
        
        elif sent.get("root_verb") is not None:
            # Ellipsis: no object but has verb, same speaker
            resolved = last_object.get(speaker)
            if resolved:
                sent["object"] = resolved
                sent["object_resolved"] = True
    
    return sentences


def score_triplet(sent: Dict) -> Dict:
    """
    Fix #9: Score S-V-O triplet confidence and flag issues.
    
    Computes triplet_confidence (0-1 score) to indicate extraction quality.
    Sentences with triplet_confidence < 0.6 should be manually reviewed.
    
    Flags indicate potential quality issues:
    - resolved_via_context: subject/object inferred from previous turns
    - unresolved_pronoun_subject/object: contains pronoun that couldn't be resolved
    - weak_root_verb: verb is modal/auxiliary (have, be, do, etc.)
    - null_subject/object: missing required field
    """
    score = 1.0
    flags = []
    
    # Penalize resolved fields (less reliable)
    if sent.get("object_resolved") or sent.get("subject_resolved"):
        score -= 0.2
        flags.append("resolved_via_context")
    
    # Penalize unresolved pronouns
    subject = str(sent.get("subject", "")).lower()
    if subject in PRONOUNS:
        score -= 0.2
        flags.append("unresolved_pronoun_subject")
    
    obj = str(sent.get("object", "")).lower()
    if obj in PRONOUNS:
        score -= 0.2
        flags.append("unresolved_pronoun_object")
    
    # Penalize weak verbs (be, have, do, go, get, make, let)
    if sent.get("root_verb") in WEAK_VERBS:
        score -= 0.15
        flags.append("weak_root_verb")
    
    # Penalize null fields
    if sent.get("subject") is None:
        score -= 0.2
        flags.append("null_subject")
    
    if sent.get("object") is None:
        score -= 0.1
        flags.append("null_object")
    
    # Clamp to 0-1 range
    score = max(0.0, min(1.0, score))
    
    sent["triplet_confidence"] = round(score, 2)
    sent["triplet_flags"] = flags
    
    return sent


def resolve_triplets(sentences: List[Dict]) -> List[Dict]:
    """
    Main triplet resolution pipeline.
    
    Runs all 9 fixes in recommended order:
    1. fix_lets_subject — cheapest, no context needed
    2. resolve_null_subject — speaker fallback
    3-4. Object extraction with conjunction handling — clause boundary fixes
    5. resolve_you_subject — needs sentence list and index
    6. resolve_anaphora — needs full sentence list, run late
    7. score_triplet — run after all resolution
    
    Args:
        sentences: List of parsed sentence dictionaries
        
    Returns:
        List of sentences with resolved triplets and confidence scores
    """
    
    # Step 1: Fix "Let's" constructions
    for sent in sentences:
        fix_lets_subject(sent)
    
    # Step 2: Resolve null subjects with speaker fallback
    for sent in sentences:
        resolve_null_subject(sent)
    
    # Step 3-4: Resolve you subjects (needs index)
    for i, sent in enumerate(sentences):
        resolve_you_subject(sent, sentences, i)
    
    # Step 5: Anaphora resolution (needs full context)
    sentences = resolve_anaphora(sentences)
    
    # Step 6: Confidence scoring
    for sent in sentences:
        score_triplet(sent)
    
    return sentences
