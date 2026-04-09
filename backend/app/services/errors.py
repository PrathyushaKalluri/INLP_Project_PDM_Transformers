from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error with stable machine-readable code."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        code: str,
        details: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.details = details or {}


def not_found(resource: str) -> AppError:
    return AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found.",
        code="NOT_FOUND",
        details={"resource": resource},
    )


def forbidden(detail: str = "You do not have permission to perform this action.") -> AppError:
    return AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        code="FORBIDDEN",
    )


def conflict(detail: str) -> AppError:
    return AppError(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
        code="CONFLICT",
    )


def bad_request(detail: str) -> AppError:
    return AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
        code="BAD_REQUEST",
    )
