"""Base repository helpers for Beanie documents."""
from typing import Any
from datetime import datetime, timezone
from beanie import Document, PydanticObjectId


async def get_by_id(model: type[Document], id: str) -> Document | None:
    try:
        return await model.get(PydanticObjectId(id))
    except Exception:
        return None


async def save_fields(doc: Document, **kwargs: Any) -> Document:
    """Update select fields and save the document."""
    for key, value in kwargs.items():
        setattr(doc, key, value)
    if hasattr(doc, "updated_at"):
        doc.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    await doc.save()
    return doc
