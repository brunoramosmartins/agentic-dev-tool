"""Routes requests by operational mode (execution vs supervised)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adt.models.schemas import QueryRequest

if TYPE_CHECKING:
    pass


class ModeRouter:
    """Determine which supervisor path to use based on ``request.mode``."""

    @staticmethod
    def is_supervised(request: QueryRequest) -> bool:
        """Return True when the request should follow the supervised path."""
        return request.mode == "supervised"
