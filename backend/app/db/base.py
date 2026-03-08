from datetime import datetime, timezone


class TimestampMixin:
    """Adds created_at / updated_at fields for Beanie documents."""

    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    @classmethod
    def _now(cls) -> datetime:
        return datetime.now(timezone.utc)
