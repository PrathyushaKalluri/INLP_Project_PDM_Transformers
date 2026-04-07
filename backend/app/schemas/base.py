from typing import Annotated

from pydantic import BeforeValidator

# Drop-in replacement for `str` fields that hold MongoDB ObjectIds.
# BeforeValidator(str) calls str() on the PydanticObjectId value before
# Pydantic's own str validation, so ObjectId → "..." works transparently.
PyObjectId = Annotated[str, BeforeValidator(str)]
