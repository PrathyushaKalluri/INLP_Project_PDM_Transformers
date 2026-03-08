from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error."""


def not_found(resource: str) -> AppError:
    return AppError(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found.")


def forbidden(detail: str = "You do not have permission to perform this action.") -> AppError:
    return AppError(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def conflict(detail: str) -> AppError:
    return AppError(status_code=status.HTTP_409_CONFLICT, detail=detail)


def bad_request(detail: str) -> AppError:
    return AppError(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
