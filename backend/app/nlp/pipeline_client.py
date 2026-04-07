"""
NLP Pipeline Client — adapter that wraps the meeting-action-extractor pipeline.

The pipeline lives at: ../meeting-action-extractor/src/pipeline.py

Expected pipeline output structure:
{
    "summary": {
        "summary_text": "...",
        "key_points": ["...", ...],
        "decisions": ["...", ...]
    },
    "action_items": [
        {
            "title": "...",
            "description": "...",
            "assignee": "...",       # raw speaker/name string
            "deadline": "YYYY-MM-DD" | null,
            "speaker": "...",
            "quote": "...",
            "timestamp": "HH:MM:SS" | null
        },
        ...
    ]
}

If the pipeline is unavailable or raises an exception, a fallback stub is used
so the rest of the system continues to work during development.
"""

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class NLPPipelineClient:
    """Wraps the NLP pipeline as an in-process service."""

    def __init__(self) -> None:
        self._pipeline_fn = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        pipeline_path = Path(settings.NLP_PIPELINE_PATH) / "pipeline.py"
        if not pipeline_path.exists():
            logger.warning(
                "NLP pipeline not found at %s — using stub mode.", pipeline_path
            )
            self._loaded = True
            return

        spec = importlib.util.spec_from_file_location("nlp_pipeline", pipeline_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        # Add parent folder to sys.path so pipeline can import its siblings
        sys.path.insert(0, str(pipeline_path.parent))
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        if hasattr(module, "run_pipeline"):
            self._pipeline_fn = module.run_pipeline
            logger.info("NLP pipeline loaded from %s", pipeline_path)
        else:
            logger.warning("pipeline.py has no run_pipeline() function — using stub mode.")
        self._loaded = True

    def process(self, transcript_text: str) -> dict[str, Any]:
        """
        Run the NLP pipeline on transcript_text.
        Returns a dict with 'summary' and 'action_items'.
        Falls back to a stub if the pipeline is unavailable.
        """
        self._load()
        if self._pipeline_fn is not None:
            try:
                result = self._pipeline_fn(transcript_text)
                # Accept both dict and JSON string responses
                if isinstance(result, str):
                    result = json.loads(result)
                return result
            except Exception as exc:
                logger.error("NLP pipeline raised an error: %s", exc, exc_info=True)
                return self._stub_response(transcript_text)
        return self._stub_response(transcript_text)

    @staticmethod
    def _stub_response(text: str) -> dict[str, Any]:
        """Minimal stub so the system works when the NLP pipeline is absent."""
        return {
            "summary": {
                "summary_text": "[NLP pipeline unavailable — summary not generated]",
                "key_points": [],
                "decisions": [],
            },
            "action_items": [],
        }


# Module-level singleton
nlp_client = NLPPipelineClient()
