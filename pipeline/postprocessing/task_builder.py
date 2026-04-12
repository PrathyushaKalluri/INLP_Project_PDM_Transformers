"""Build structured task objects with description generation."""

import os
import re
from typing import List, Dict, Optional

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MODEL_NAME = "google/flan-t5-base"

TASK_PROMPT = (
    "Convert the following meeting discussion into one short action item. "
    "Remove names, pronouns, and conversational language. "
    "Start with an imperative verb. Output only one sentence.\n\n"
    "Discussion:\n{text}\n\n"
    "Action item:"
)

# Verb lemma to imperative form
VERB_IMPERATIVES = {
    "look": "Investigate",
    "monitor": "Monitor", 
    "revisit": "Revisit",
    "keep": "Continue monitoring",
    "follow": "Follow up on",
    "check": "Check",
    "review": "Review",
    "deploy": "Deploy",
    "write": "Write",
    "create": "Create",
    "build": "Build",
    "fix": "Fix",
    "test": "Test",
    "update": "Update",
    "send": "Send",
    "prepare": "Prepare",
    "schedule": "Schedule",
    "organize": "Organize",
    "coordinate": "Coordinate",
    "finalize": "Finalize",
    "implement": "Implement",
    "document": "Document",
    "design": "Design",
    "refactor": "Refactor",
    "audit": "Audit",
    "add": "Add",
    "draft": "Draft",
    "redesign": "Redesign",
    "investigate": "Investigate",
    "analyze": "Analyze",
    "verify": "Verify",
    "validate": "Validate",
    "plan": "Plan",
    "propose": "Propose",
    "suggest": "Suggest",
    "summarize": "Summarize",
    "compile": "Compile",
    "generate": "Generate",
    "migrate": "Migrate",
    "integrate": "Integrate",
    "optimize": "Optimize",
    "debug": "Debug",
    "resolve": "Resolve",
    "improve": "Improve",
    "establish": "Establish",
    "run": "Run",
    "submit": "Submit",
    "develop": "Develop",
    "maintain": "Maintain",
    "prioritize": "Prioritize",
}

ACTION_VERBS = re.compile(
    r"\b(handle|fix|write|create|update|review|deploy|test|configure"
    r"|audit|document|design|build|refactor|implement|prepare|set\s+up"
    r"|increase|add|draft|redesign|look\s+into|investigate|check"
    r"|monitor|migrate|integrate|optimize|schedule|resolve|improve"
    r"|analyze|coordinate|establish|run|send|submit|develop|maintain|prioritize)\b",
    re.I,
)

NON_TASK_PATTERNS = [
    re.compile(r"^\s*good\s+(morning|afternoon|evening)\b", re.I),
    re.compile(r"^\s*(hi|hello|hey|welcome)\b", re.I),
    re.compile(r"\b(meet\s+again|schedule\s+(a\s+)?follow.?up)\b", re.I),
    re.compile(r"^\s*(sounds?\s+good|perfect|great|agreed)\b", re.I),
]

CONVERSATIONAL_PATTERNS = [
    r"^i\s+think\s+",
    r"^we\s+should\s+",
    r"^I\s+will\s+",
    r"^you\s+should\s+",
    r"^i\s+need\s+to\s+",
    r"^i\s+m\s+going\s+to\s+",
    r"^we\s+ll\s+",
]

FILLER_WORDS = [
    r"\bfirst\b", r"\bjust\b", r"\bactually\b", r"\bbasically\b",
    r"\bprobably\b", r"\bdefinitely\b", r"\bkind of\b", r"\bsort of\b",
]

DAYS_OF_WEEK = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

NON_TASK_PATTERNS = [
    re.compile(r"^\s*good\s+(morning|afternoon|evening)\b", re.I),
    re.compile(r"^\s*(hi|hello|hey|welcome)\b", re.I),
    re.compile(r"\b(meet\s+again|schedule\s+(a\s+)?follow.?up)\b", re.I),
    re.compile(r"^\s*(sounds?\s+good|perfect|great|agreed)\b", re.I),
]

CONVERSATIONAL_PATTERNS = [
    r"^i\s+think\s+",
    r"^we\s+should\s+",
    r"^I\s+will\s+",
    r"^you\s+should\s+",
    r"^i\s+need\s+to\s+",
    r"^i'?m\s+going\s+to\s+",
    r"^we'?ll\s+",
]

FILLER_WORDS = [
    r"\bfirst\b", r"\bjust\b", r"\bactually\b", r"\bbasically\b",
    r"\bprobably\b", r"\bdefinitely\b", r"\bkind of\b", r"\bsort of\b",
]

DAYS_OF_WEEK = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def build_task_title_from_triplet(sentence_data: Dict) -> Optional[str]:
    """
    Build task title using verb imperative + object from dependency triplet.
    
    Args:
        sentence_data (Dict): Sentence with keys like 'root_verb', 'object', 'text'
    
    Returns:
        str: Generated task title or None
    
    Examples:
        {"root_verb": "look", "object": "churn"} → "Investigate churn"
        {"root_verb": "monitor", "object": "integration progress"} → "Monitor integration progress"
        {"root_verb": "revisit", "object": "churn issue"} → "Revisit churn issue"
    """
    verb = sentence_data.get("root_verb", "").lower() if sentence_data.get("root_verb") else ""
    obj = sentence_data.get("object", "").strip() if sentence_data.get("object") else ""
    
    if not verb:
        return None
    
    # Get imperative form of verb
    imperative = VERB_IMPERATIVES.get(verb, verb.capitalize())
    
    # Build title
    if obj:
        # Capitalize first letter of object if not already
        obj_text = obj[0].upper() + obj[1:] if obj else ""
        title = f"{imperative} {obj_text}"
    else:
        title = imperative
    
    # Ensure title ends with period
    if not title.endswith("."):
        title += "."
    
    return title


def is_valid_task_title(title: str, root_verb: Optional[str] = None, obj: Optional[str] = None) -> bool:
    """
    Check if a task title is valid (not a broken triplet or garbage).
    
    Rejects titles that are:
    - Single words (no clear action/object)
    - Weak verbs with no/pronoun object
    - Questions
    - Pure numbers
    - Pronouns only
    
    Args:
        title: Task title/description
        root_verb: Optional root verb for semantic checking
        obj: Optional object for semantic checking
    
    Returns:
        bool: True if title is valid as a task
    
    Examples:
        "Investigate churn" → True
        "Be." → False (weak verb, no object)
        "Go." → False (single word)
        "Need 2000." → False (object is number)
        "Be Status." → False (weak verb, weak object)
        "Think The DevOps team." → False (weak verb)
        "Deploy the API" → True
    """
    # Weak verbs that rarely result in valid tasks
    weak_verbs = {"be", "have", "do", "go", "get", "make", "seem", "appear",
                  "look", "feel", "become", "need", "think", "know"}
    
    # Pronouns and non-objects
    invalid_objects = {
        "that", "it", "this", "them", "those", "these",
        "something", "anything", "nothing", "everything",
        "one", "he", "she", "they", "we", "i",
    }
    
    if not title or len(title.strip()) == 0:
        return False
    
    title_clean = title.strip().rstrip(".")
    words = title_clean.split()
    
    # Single word titles are never valid tasks
    if len(words) <= 1:
        return False
    
    # Title is a question
    if title.strip().endswith("?"):
        return False
    
    # Check if last word is all digits (e.g., "Need 2000")
    if words[-1].isdigit():
        return False
    
    # Check for weak verb with no valid object
    if root_verb and root_verb.lower() in weak_verbs:
        if not obj or obj.lower() in invalid_objects:
            return False
    
    return True



# ── Task Description Generator ──
# Shared model cache variables (module-level) to enable model reuse across instances
# On first cold-start, FLAN-T5 model loading takes ~15-20s; subsequent calls use cache
# Publish endpoint timeout was increased to 60s to handle this cold-start period
_SHARED_TASK_MODEL = None
_SHARED_TASK_TOKENIZER = None
_SHARED_TASK_DEVICE = None


class TaskDescriptionGenerator:
    """Generate task descriptions from sentence text using FLAN-T5."""

    def __init__(self, model_name: str = MODEL_NAME):
        """Initialize task description generator."""
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._device = None
        self._torch = None
    
    def _ensure_loaded(self):
        """Lazy-load FLAN-T5 model on first use.
        
        Uses global cached model/tokenizer/device to avoid memory overhead of multiple model instances.
        On first call: loads spaCy + transformers models (~15-20s, now covered by 60s publish timeout)
        On subsequent calls: reuses cached models via global module variables
        """
        global _SHARED_TASK_MODEL, _SHARED_TASK_TOKENIZER, _SHARED_TASK_DEVICE

        if self._model is not None:
            return
        
        try:
            if _SHARED_TASK_MODEL is None or _SHARED_TASK_TOKENIZER is None or _SHARED_TASK_DEVICE is None:
                print(f"[*] Loading summarization model: {self.model_name}")
                import torch
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

                torch.set_num_threads(1)
                _SHARED_TASK_DEVICE = torch.device("cpu")
                self._torch = torch

                _SHARED_TASK_TOKENIZER = AutoTokenizer.from_pretrained(self.model_name)
                _SHARED_TASK_MODEL = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name,
                    dtype=torch.float32,
                    low_cpu_mem_usage=False,
                )
                _SHARED_TASK_MODEL.to(_SHARED_TASK_DEVICE)
                _SHARED_TASK_MODEL.eval()

            self._tokenizer = _SHARED_TASK_TOKENIZER
            self._model = _SHARED_TASK_MODEL
            self._device = _SHARED_TASK_DEVICE
            print(f"[+] Summarization model loaded")
        except Exception as e:
            print(f"[!] Warning: Could not load summarization model: {e}")
            print(f"[!] Falling back to rule-based cleaning")
    
    def _rule_based_clean(self, text: str) -> str:
        """Clean text to task using rules."""
        cleaned = text.strip()
        
        # Keep first sentence only
        for sep in [". ", "? ", "! "]:
            if sep in cleaned:
                cleaned = cleaned[:cleaned.index(sep)].strip()
        
        # Remove conversational prefixes
        for pattern in CONVERSATIONAL_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
        # Remove filler words
        for pattern in FILLER_WORDS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        
        # Collapse spaces
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = cleaned.rstrip("?").rstrip(".").strip()
        
        # Capitalize days/months
        for day in DAYS_OF_WEEK:
            cleaned = re.sub(rf"\b{day}\b", day.capitalize(), cleaned, flags=re.IGNORECASE)
        for month in MONTHS:
            cleaned = re.sub(rf"\b{month}\b", month.capitalize(), cleaned, flags=re.IGNORECASE)
        
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        if cleaned and not cleaned.endswith("."):
            cleaned += "."
        
        return cleaned
    
    def _is_valid_task(self, text: str) -> bool:
        """Check if text is a valid task description."""
        if not text or len(text.split()) < 3:
            return False
        
        for pat in NON_TASK_PATTERNS:
            if pat.search(text):
                return False
        
        if not ACTION_VERBS.search(text):
            return False
        
        return True
    
    def generate(self, text: str) -> Optional[str]:
        """
        Generate task description from text.
        
        Args:
            text (str): Raw sentence text or discussion
        
        Returns:
            str: Task description or None
        """
        if not text:
            return None
        
        try:
            self._ensure_loaded()
            
            if self._model is None:
                return self._rule_based_clean(text)
            
            prompt = TASK_PROMPT.format(text=text)
            inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            with self._torch.no_grad():
                outputs = self._model.generate(
                    inputs["input_ids"],
                    max_length=100,
                    num_beams=1,
                    temperature=1.0,
                )
            
            task_desc = self._tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            
            if not self._is_valid_task(task_desc):
                task_desc = self._rule_based_clean(text)
            
            return task_desc
        except Exception as e:
            print(f"[!] Generation failed: {e}")
            return self._rule_based_clean(text)


class TaskBuilder:
    """
    Builds structured task objects from extracted components.
    Includes description generation during task building.
    """
    
    def __init__(self):
        """Initialize task builder with description generator."""
        self.desc_gen = TaskDescriptionGenerator()
    
    @staticmethod
    def build_task(
        task_id: str,
        description: str,
        assignee: Optional[str] = None,
        deadline: Optional[str] = None,
        confidence: float = 1.0,
        evidence: Optional[Dict] = None,
    ) -> Dict:
        """
        Build a structured task dictionary.
        
        Args:
            task_id (str): Unique task identifier
            description (str): Task description text
            assignee (str): Person responsible
            deadline (str): When task should be completed
            confidence (float): Confidence score (0-1)
            evidence (Dict): Evidence information (text, speaker, etc.)
        
        Returns:
            Dict: Structured task object
        """
        return {
            "task_id": task_id,
            "task": description,
            "assignee": assignee,
            "deadline": deadline,
            "confidence": confidence,
            "evidence": evidence or {},
        }
    
    @staticmethod
    def build_batch(
        task_definitions: List[Dict],
    ) -> List[Dict]:
        """
        Build multiple task objects from extracted metadata.
        
        Includes validity checking to filter out broken triplets and garbage titles.
        
        Args:
            task_definitions (List[Dict]): List of task definition dicts
                        with keys: description, assignee, deadline, confidence, evidence,
                        root_verb (optional), object (optional)
        
        Returns:
            List[Dict]: Structured task objects (only valid titles)
        """
        builder = TaskBuilder()
        tasks = []
        task_id = 1
        
        for task_def in task_definitions:
            # Try to generate title using triplet (if available)
            description = None
            if task_def.get("root_verb") or task_def.get("object"):
                description = build_task_title_from_triplet(task_def)
                
                # Check if triplet-generated title is valid
                if description and not is_valid_task_title(
                    description,
                    root_verb=task_def.get("root_verb"),
                    obj=task_def.get("object")
                ):
                    description = None  # Reject broken triplet, try fallback
            
            # Fall back to description generation if triplet didn't work
            if not description:
                raw_text = task_def.get("raw_text", task_def.get("description", ""))
                description = builder.desc_gen.generate(raw_text)
            
            if not description:
                description = task_def.get("description", "")
            
            # Final validity check on description
            if description and is_valid_task_title(description):
                task = TaskBuilder.build_task(
                    task_id=f"task_{task_id}",
                    description=description,
                    assignee=task_def.get("assignee"),
                    deadline=task_def.get("deadline"),
                    confidence=task_def.get("confidence", 1.0),
                    evidence=task_def.get("evidence"),
                )
                tasks.append(task)
                task_id += 1
        
        return tasks

