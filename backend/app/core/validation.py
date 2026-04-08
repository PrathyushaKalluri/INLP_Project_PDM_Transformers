"""
Contract Validation — development-mode audit layer.

Validates that frontend adapter responses match the expected schema contract.
Only active when ENV=development. Logs warnings; does NOT block responses.

This catches contract drift early during development without affecting production.
"""

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Expected response schemas for frontend adapter endpoints ─────────────────

_FRONTEND_CONTRACTS: dict[str, dict[str, Any]] = {
    # Auth
    "POST /auth/login": {
        "required_keys": {"user", "token"},
        "nested": {"user": {"required_keys": {"id", "email", "fullName"}}},
    },
    "POST /auth/signup": {
        "required_keys": {"id", "email", "fullName"},
    },
    "GET /auth/me": {
        "required_keys": {"id", "email", "fullName", "isActive"},
    },

    # Projects (list returns array — validated separately)
    "GET /projects": {"is_array": True},

    # Tasks (list returns array)
    "GET /tasks": {"is_array": True},

    # Transcripts (list returns array)
    "GET /transcripts": {"is_array": True},

    # Processing status
    "GET /processing/*/status": {
        "required_keys": {"jobId", "status", "currentStep", "stepLabel", "progress"},
    },

    # Notifications
    "GET /notifications": {"is_array": True},
}


def _match_contract(method: str, path: str) -> dict[str, Any] | None:
    """Find a matching contract for the given method & path."""
    # Exact match first
    key = f"{method} {path}"
    if key in _FRONTEND_CONTRACTS:
        return _FRONTEND_CONTRACTS[key]

    # Wildcard match (for paths like /processing/{id}/status)
    for pattern, contract in _FRONTEND_CONTRACTS.items():
        pattern_method, pattern_path = pattern.split(" ", 1)
        if pattern_method != method:
            continue
        if "*" in pattern_path:
            parts = pattern_path.split("*")
            if len(parts) == 2 and path.startswith(parts[0]) and path.endswith(parts[1]):
                return contract
    return None


def _validate_response_body(body: Any, contract: dict[str, Any], path: str) -> list[str]:
    """Validate response body against contract. Returns list of violation messages."""
    violations: list[str] = []

    if contract.get("is_array"):
        if not isinstance(body, list):
            violations.append(f"{path}: expected array, got {type(body).__name__}")
        return violations

    required_keys = contract.get("required_keys", set())
    if required_keys:
        if not isinstance(body, dict):
            violations.append(f"{path}: expected object, got {type(body).__name__}")
            return violations
        missing = required_keys - set(body.keys())
        if missing:
            violations.append(f"{path}: missing required keys: {missing}")

    nested = contract.get("nested", {})
    if isinstance(body, dict):
        for key, sub_contract in nested.items():
            if key in body:
                sub_violations = _validate_response_body(body[key], sub_contract, f"{path}.{key}")
                violations.extend(sub_violations)

    return violations


class ContractValidationMiddleware(BaseHTTPMiddleware):
    """
    Development-mode middleware that logs warnings when frontend adapter
    responses drift from the expected schema contract.

    Only active when ENV=development.
    """

    async def __call__(self, scope, receive, send):
        # BaseHTTPMiddleware natively drops/corrupts websockets in many Starlette versions.
        # We explicitly bypass this middleware entirely for non-HTTP traffic.
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        await super().__call__(scope, receive, send)

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Only validate in development mode
        if settings.ENV.lower() != "development":
            return response

        # Only validate frontend adapter routes (not /api/v1/*)
        path = request.url.path
        if path.startswith("/api/"):
            return response

        method = request.method
        contract = _match_contract(method, path)
        if not contract:
            return response

        # We can only validate JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # For streaming responses, we cannot easily inspect the body
        # without consuming it, so we skip validation for those
        if not hasattr(response, "body"):
            return response

        try:
            import json
            body = json.loads(response.body)
            violations = _validate_response_body(body, contract, f"{method} {path}")
            for v in violations:
                logger.warning("CONTRACT DRIFT: %s", v)
        except Exception:
            pass  # Don't break anything if validation itself fails

        return response
