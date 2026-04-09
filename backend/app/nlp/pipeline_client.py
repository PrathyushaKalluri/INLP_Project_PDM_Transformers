"""NLP pipeline adapter for in-process execution."""

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
            raise RuntimeError(f"NLP pipeline not found at {pipeline_path}")

        spec = importlib.util.spec_from_file_location("nlp_pipeline", pipeline_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        # Add parent folder to sys.path so pipeline can import its siblings
        sys.path.insert(0, str(pipeline_path.parent))
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        if hasattr(module, "run_pipeline"):
            self._pipeline_fn = module.run_pipeline
            logger.info("NLP pipeline loaded from %s", pipeline_path)
        else:
            raise RuntimeError("pipeline.py has no run_pipeline() function")
        self._loaded = True

    def process(self, transcript_text: str) -> dict[str, Any]:
        """
        Run NLP pipeline and return a dict with 'summary' and 'action_items'.
        """
        self._load()
        if self._pipeline_fn is None:
            raise RuntimeError("NLP pipeline function was not loaded")
        result = self._pipeline_fn(transcript_text)
        if isinstance(result, str):
            result = json.loads(result)
        return result


# Module-level singleton
nlp_client = NLPPipelineClient()
