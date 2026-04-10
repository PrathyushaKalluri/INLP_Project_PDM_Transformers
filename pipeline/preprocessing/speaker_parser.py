"""Extract speakers and their utterances from raw transcripts (multiple formats)."""

import re
from typing import List, Dict, Tuple, Optional


def _parse_colon_format(line: str) -> Optional[Tuple[str, str]]:
    """Parse: John: I will handle this"""
    if ':' not in line:
        return None
    
    speaker, text = line.split(':', 1)
    speaker = speaker.strip()
    text = text.strip()
    
    if speaker and text:
        return (speaker, text)
    return None


def _parse_dash_format(line: str) -> Optional[Tuple[str, str]]:
    """Parse: John - I will handle this (Zoom/Teams format)"""
    match = re.match(r'^([A-Za-z\s]+?)\s+-\s+(.+)$', line.strip())
    
    if match:
        speaker = match.group(1).strip()
        text = match.group(2).strip()
        if speaker and text:
            return (speaker, text)
    
    return None


def _parse_timestamp_format(line: str) -> Optional[Tuple[str, str, str]]:
    """Parse: [00:03:12] John: I will handle this"""
    match = re.match(r'^\[(\d{1,2}:\d{2}:\d{2})\]\s*(.+?):\s*(.+)$', line.strip())
    
    if match:
        timestamp = match.group(1)
        speaker = match.group(2).strip()
        text = match.group(3).strip()
        if speaker and text:
            return (timestamp, speaker, text)
    
    return None


def parse_speakers(transcript: str) -> List[Dict]:
    """
    Parse speaker and text pairs from raw transcript (multiple formats).
    
    Supports:
    - Colon format: "John: I will handle this"
    - Dash format: "John - I will handle this"
    - Timestamp format: "[00:03:12] John: I will handle this"
    
    Args:
        transcript (str): Raw transcript text
    
    Returns:
        List[Dict]: List of turn dictionaries with keys:
                   - turn_id (int): Sequential turn number
                   - speaker (str): Speaker name or "unknown"
                   - timestamp (str or None): Timestamp if present
                   - text (str): Utterance text
    """
    speakers = []
    lines = transcript.strip().split('\n')
    turn_id = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try timestamp format first
        timestamp_result = _parse_timestamp_format(line)
        if timestamp_result:
            timestamp, speaker, text = timestamp_result
            speakers.append({
                "turn_id": turn_id,
                "speaker": speaker,
                "timestamp": timestamp,
                "text": text
            })
            turn_id += 1
            continue
        
        # Try colon format
        colon_result = _parse_colon_format(line)
        if colon_result:
            speaker, text = colon_result
            speakers.append({
                "turn_id": turn_id,
                "speaker": speaker,
                "timestamp": None,
                "text": text
            })
            turn_id += 1
            continue
        
        # Try dash format
        dash_result = _parse_dash_format(line)
        if dash_result:
            speaker, text = dash_result
            speakers.append({
                "turn_id": turn_id,
                "speaker": speaker,
                "timestamp": None,
                "text": text
            })
            turn_id += 1
            continue

        # Fallback for lines without explicit speaker markers.
        # Keep text instead of dropping it, otherwise downstream extraction can become empty.
        if speakers:
            # Treat as continuation of the previous turn.
            prev_text = speakers[-1].get("text", "")
            speakers[-1]["text"] = f"{prev_text} {line}".strip()
        else:
            speakers.append({
                "turn_id": turn_id,
                "speaker": "unknown",
                "timestamp": None,
                "text": line,
            })
            turn_id += 1
    
    if not speakers:
        print("[!] Warning: No speakers detected. Check transcript format.")
    
    return speakers

