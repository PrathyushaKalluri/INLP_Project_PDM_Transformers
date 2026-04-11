"""
NLP Service — Abstraction over local pipeline and remote HTTP service.

Handles:
- Dual execution mode (local / service)
- Timeout wrapping
- Output schema validation
- Retry logic for transient service errors
"""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.nlp.pipeline_client import nlp_client
from app.services.errors import bad_request

logger = logging.getLogger(__name__)

# ── NLP output contract ──────────────────────────────────────────────────────

_REQUIRED_ACTION_ITEM_FIELDS = {"title"}


def validate_nlp_output(result: Any) -> dict:
    """
    Validate and normalise an NLP pipeline result.

    Expected shape:
        {
            "summary": {"summary_text": str, "key_points": [...], "decisions": [...]},
            "action_items": [{"title": str, ...}, ...]
        }

    Raises ValueError on schema mismatch so the caller can mark the job FAILED.
    """
    if not isinstance(result, dict):
        raise ValueError(f"NLP output must be a dict, got {type(result).__name__}")

    # ── summary ──────────────────────────────────────────────────────────
    summary = result.get("summary")
    if summary is not None and not isinstance(summary, dict):
        raise ValueError(f"'summary' must be a dict, got {type(summary).__name__}")
    if summary is None:
        logger.warning("NLP output has no 'summary' — using empty default.")
        result["summary"] = {"summary_text": None, "key_points": [], "decisions": []}

    # ── action_items ─────────────────────────────────────────────────────
    items = result.get("action_items")
    if items is not None and not isinstance(items, list):
        raise ValueError(f"'action_items' must be a list, got {type(items).__name__}")
    if items is None:
        logger.warning("NLP output has no 'action_items' — using empty list.")
        result["action_items"] = []

    valid_items = []
    for idx, item in enumerate(result["action_items"]):
        if not isinstance(item, dict):
            logger.warning("action_items[%d] is not a dict; discarding.", idx)
            continue
        title = item.get("title", "")
        if not title or not str(title).strip():
            logger.warning("action_items[%d] has no meaningful title; discarding.", idx)
            continue
        valid_items.append(item)
    
    result["action_items"] = valid_items

    return result


# ── Data mapping layer (STEP 3: Phase Z Guarantees) ─────────────────────────

from datetime import date, datetime

def map_action_item(item: dict, project_id: str | None = None) -> dict:
    """
    Map NLP action item to normalized system format.
    
    Handles:
    - assignee: Keep as string or None (will be resolved to user_id later)
    - deadline: Convert to ISO format string or None
    
    Args:
        item: Raw action item from NLP
        project_id: Optional project context
        
    Returns:
        dict: Normalized action item with guaranteed fields
        
    Fallbacks:
        - unknown assignee → None
        - invalid deadline → None
    """
    mapped = {
        "title": item.get("title", "Untitled"),
        "description": item.get("description", ""),
        "assignee": None,
        "deadline": None,
    }
    
    # ── Assignee mapping ──────────────────────────────────────────────
    assignee_raw = item.get("assignee")
    if assignee_raw:
        assignee_str = str(assignee_raw).strip() if assignee_raw else None
        # Keep assignee as string name; backend will resolve to user_id
        if assignee_str and assignee_str.lower() not in {"unknown", "none", "team", ""}:
            mapped["assignee"] = assignee_str
    
    # ── Deadline mapping ──────────────────────────────────────────────
    deadline_raw = item.get("deadline")
    if deadline_raw:
        try:
            # Handle date object
            if isinstance(deadline_raw, date):
                mapped["deadline"] = deadline_raw.isoformat()
            # Handle string (ISO format expected)
            elif isinstance(deadline_raw, str):
                # Try to parse and re-serialize to validate
                parsed = date.fromisoformat(deadline_raw.strip())
                mapped["deadline"] = parsed.isoformat()
            # Handle datetime
            elif isinstance(deadline_raw, datetime):
                mapped["deadline"] = deadline_raw.date().isoformat()
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning("Could not map deadline '%s': %s — skipping.", deadline_raw, e)
            mapped["deadline"] = None
    
    return mapped


def map_pipeline_output(result: dict, project_id: str | None = None) -> dict:
    """
    Apply mapping layer to normalize entire NLP output.
    
    Maps all action items and ensures consistent structure.
    
    Args:
        result: Validated NLP output
        project_id: Optional project context
        
    Returns:
        dict: Mapped result with normalized action items
    """
    mapped_result = dict(result)  # shallow copy
    
    # Map each action item
    action_items = result.get("action_items", [])
    mapped_action_items = []
    
    for item in action_items:
        try:
            mapped_item = map_action_item(item, project_id)
            mapped_action_items.append(mapped_item)
        except Exception as e:
            logger.warning("Failed to map action item: %s — skipping.", e)
            continue
    
    mapped_result["action_items"] = mapped_action_items
    return mapped_result

class NLPService:
    """
    Unified NLP execution layer.  Supports `local` (in-process Python call)
    and `service` (HTTP to external pipeline) modes.
    """

    async def process(self, transcript_text: str, project_id: str | None = None) -> dict:
        """
        Run NLP and return validated + mapped result dict.

        Raises:
            asyncio.TimeoutError   — if pipeline exceeds configured timeout
            ValueError             — if output schema is invalid
            RuntimeError           — if pipeline itself fails
            bad_request (AppError) — if NLP_MODE is unsupported
            
        Args:
            transcript_text: Raw meeting transcript
            project_id: Optional project context for mapping
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[NLP_SERVICE] Starting NLP process for {len(transcript_text)} chars")
        
        mode = settings.NLP_MODE.strip().lower()
        logger.debug(f"[NLP_SERVICE] Using NLP_MODE: {mode}")
        
        if mode == "local":
            logger.info(f"[NLP_SERVICE] Processing in LOCAL mode")
            result = await self._process_local(transcript_text)
        elif mode == "service":
            logger.info(f"[NLP_SERVICE] Processing via SERVICE mode")
            result = await self._process_via_service(transcript_text)
        else:
            logger.error(f"[NLP_SERVICE] Unsupported NLP_MODE '{settings.NLP_MODE}'")
            raise bad_request(f"Unsupported NLP_MODE '{settings.NLP_MODE}'.")

        logger.info(f"[NLP_SERVICE] Pipeline returned result with keys: {list(result.keys()) if result else 'None'}")
        
        # Step 1: Validate
        logger.info(f"[NLP_SERVICE] Validating output...")
        try:
            validated = validate_nlp_output(result)
            logger.info(f"[NLP_SERVICE] ✓ Validation passed")
        except Exception as e:
            logger.error(f"[NLP_SERVICE] ✗ Validation failed: {e}", exc_info=True)
            raise
        
        # Step 2: Map (normalize assignees, deadlines)
        logger.info(f"[NLP_SERVICE] Mapping output...")
        try:
            mapped = map_pipeline_output(validated, project_id)
            logger.info(f"[NLP_SERVICE] ✓ Mapping complete, result keys: {list(mapped.keys())}")
        except Exception as e:
            logger.error(f"[NLP_SERVICE] ✗ Mapping failed: {e}", exc_info=True)
            raise
        
        logger.info(f"[NLP_SERVICE] ✓ NLP process complete")
        return mapped

    # ── local mode ───────────────────────────────────────────────────────

    async def _process_local(self, transcript_text: str) -> dict:
        """
        Run local pipeline with a timeout guard.
        The pipeline is synchronous, so we run it in a thread executor.
        """
        loop = asyncio.get_running_loop()
        timeout = settings.NLP_SERVICE_TIMEOUT_SECONDS

        return await asyncio.wait_for(
            loop.run_in_executor(None, nlp_client.process, transcript_text),
            timeout=timeout,
        )

    # ── service mode ─────────────────────────────────────────────────────

    async def _process_via_service(self, transcript_text: str) -> dict:
        timeout = settings.NLP_SERVICE_TIMEOUT_SECONDS
        max_retries = 2  # retry up to 2 times on transient HTTP errors

        async with httpx.AsyncClient(timeout=timeout) as client:
            # ── submit job ───────────────────────────────────────────
            start_resp = await self._http_with_retry(
                client, "POST",
                f"{settings.NLP_SERVICE_BASE_URL}/v1/process",
                json={"meeting_id": "backend-job", "text": transcript_text},
                retries=max_retries,
            )
            job_id = start_resp.get("job_id")
            if not job_id:
                raise RuntimeError("Pipeline service did not return job_id.")

            # ── poll for completion ──────────────────────────────────
            max_tries = max(
                1,
                settings.NLP_SERVICE_MAX_POLL_SECONDS
                // settings.NLP_SERVICE_POLL_INTERVAL_SECONDS,
            )
            for attempt in range(max_tries):
                status_resp = await self._http_with_retry(
                    client, "GET",
                    f"{settings.NLP_SERVICE_BASE_URL}/v1/jobs/{job_id}",
                    retries=max_retries,
                )
                state = status_resp.get("status", "").upper()
                if state == "COMPLETED":
                    result_resp = await self._http_with_retry(
                        client, "GET",
                        f"{settings.NLP_SERVICE_BASE_URL}/v1/results/{job_id}",
                        retries=max_retries,
                    )
                    return result_resp
                if state in {"FAILED", "TIMEOUT", "CANCELLED"}:
                    error_detail = status_resp.get("error", state)
                    raise RuntimeError(
                        f"Pipeline service job ended with status: {state} — {error_detail}"
                    )
                await asyncio.sleep(settings.NLP_SERVICE_POLL_INTERVAL_SECONDS)

        raise TimeoutError(
            "Pipeline service job did not complete within configured max polling time."
        )

    # ── HTTP helper with retry on transient errors ───────────────────────

    @staticmethod
    async def _http_with_retry(
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        retries: int = 2,
        **kwargs,
    ) -> dict:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = await client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                # Only retry on transient server errors (5xx) or transport issues
                if isinstance(exc, httpx.TransportError) or (status and status >= 500):
                    logger.warning(
                        "NLP service %s %s attempt %d/%d failed: %s",
                        method, url, attempt + 1, retries + 1, exc,
                    )
                    if attempt < retries:
                        await asyncio.sleep(0.5 * (attempt + 1))  # shorter linear backoff
                        continue
                raise  # non-retryable error — propagate immediately
        raise last_exc  # type: ignore[misc]  # all retries exhausted
