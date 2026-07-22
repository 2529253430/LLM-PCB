from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import BuckDesignRequirements, ComponentCandidate


class ComponentSearchProvider(ABC):
    """
    Abstract interface implemented by every online or local component source.

    Provider implementations are responsible only for obtaining and normalizing
    component data. They must not contain Buck selection or ranking policy.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit: int = 50,
    ) -> List[ComponentCandidate]:
        """
        Search for Buck regulator candidates and return normalized results.

        Network authentication, pagination, rate limiting, retries, and raw API
        response parsing belong inside the concrete provider implementation.
        """

    def get_component(
        self,
        part_number: str,
        manufacturer: Optional[str] = None,
    ) -> Optional[ComponentCandidate]:
        """
        Optionally retrieve one component by exact part number.

        Providers that do not support exact lookup may keep this default
        implementation.
        """
        return None
