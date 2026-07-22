from __future__ import annotations

from typing import List

from .models import BuckDesignRequirements, ComponentCandidate
from .provider import ComponentSearchProvider


class FailingComponentSearchProvider(ComponentSearchProvider):
    """Provider used to verify manager error isolation."""

    def __init__(
        self,
        name: str = "failing-provider",
        message: str = "Simulated provider failure.",
    ) -> None:
        self._name = name
        self._message = message

    @property
    def provider_name(self) -> str:
        return self._name

    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit: int = 50,
    ) -> List[ComponentCandidate]:
        raise RuntimeError(self._message)
