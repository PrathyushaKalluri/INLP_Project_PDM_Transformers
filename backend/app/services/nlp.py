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


# ── Service class ────────────────────────────────────────────────────────────

class NLPService:
    """
    Unified NLP execution layer.  Supports `local` (in-process Python call)
    and `service` (HTTP to external pipeline) modes.
    """

    async def process(self, transcript_text: str) -> dict:
        """
        Run NLP and return validated result dict.

        Raises:
            asyncio.TimeoutError   — if pipeline exceeds configured timeout
            ValueError             — if output schema is invalid
            RuntimeError           — if pipeline itself fails
            bad_request (AppError) — if NLP_MODE is unsupported
        """
        mode = settings.NLP_MODE.strip().lower()
        if mode == "local":
            result = await self._process_local(transcript_text)
        elif mode == "service":
            result = await self._process_via_service(transcript_text)
        else:
            raise bad_request(f"Unsupported NLP_MODE '{settings.NLP_MODE}'.")

        # Validate before returning — fail loudly on schema mismatch
        return validate_nlp_output(result)

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
                        await asyncio.sleep(1 * (attempt + 1))  # linear backoff
                        continue
                raise  # non-retryable error — propagate immediately
        raise last_exc  # type: ignore[misc]  # all retries exhausted
