from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import (
    BuckDesignRequirements,
    ComponentCandidate,
    DistributorOffer,
)
from .provider import ComponentSearchProvider


@dataclass(frozen=True)
class ProviderFailure:
    """Information about one provider that failed during a search."""

    provider_name: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ProviderSearchSummary:
    """Summary of a multi-provider component search."""

    candidates: List[ComponentCandidate]
    failures: List[ProviderFailure]
    provider_result_counts: Dict[str, int]
    total_raw_candidates: int
    total_unique_candidates: int


class ProviderManager:
    """
    Coordinate searches across multiple component data providers.

    Responsibilities:
    - Call all enabled providers.
    - Isolate provider failures.
    - Normalize and merge duplicate components.
    - Merge distributor offers.
    - Return a searchable summary.

    The manager does not score electrical suitability. Ranking remains the
    responsibility of BuckComponentComparator.
    """

    def __init__(
        self,
        providers: Optional[Sequence[ComponentSearchProvider]] = None,
    ) -> None:
        self._providers: List[ComponentSearchProvider] = []
        self._enabled: Dict[str, bool] = {}

        for provider in providers or []:
            self.register(provider)

    @property
    def providers(self) -> Tuple[ComponentSearchProvider, ...]:
        return tuple(self._providers)

    def register(
        self,
        provider: ComponentSearchProvider,
        enabled: bool = True,
    ) -> None:
        name = self._normalized_provider_name(provider)

        if any(
            self._normalized_provider_name(existing) == name
            for existing in self._providers
        ):
            raise ValueError(
                f"A provider named '{provider.provider_name}' "
                "has already been registered."
            )

        self._providers.append(provider)
        self._enabled[name] = enabled

    def unregister(self, provider_name: str) -> None:
        normalized = provider_name.strip().lower()

        remaining = [
            provider
            for provider in self._providers
            if self._normalized_provider_name(provider) != normalized
        ]

        if len(remaining) == len(self._providers):
            raise KeyError(f"Unknown provider: {provider_name}")

        self._providers = remaining
        self._enabled.pop(normalized, None)

    def enable(self, provider_name: str) -> None:
        normalized = self._require_provider(provider_name)
        self._enabled[normalized] = True

    def disable(self, provider_name: str) -> None:
        normalized = self._require_provider(provider_name)
        self._enabled[normalized] = False

    def is_enabled(self, provider_name: str) -> bool:
        normalized = self._require_provider(provider_name)
        return self._enabled[normalized]

    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit_per_provider: int = 50,
        stop_on_error: bool = False,
    ) -> ProviderSearchSummary:
        requirements.validate()

        if limit_per_provider <= 0:
            raise ValueError("limit_per_provider must be greater than zero.")

        raw_candidates: List[ComponentCandidate] = []
        failures: List[ProviderFailure] = []
        provider_result_counts: Dict[str, int] = {}

        for provider in self._providers:
            normalized_name = self._normalized_provider_name(provider)

            if not self._enabled.get(normalized_name, False):
                continue

            try:
                results = provider.search_buck_regulators(
                    requirements=requirements,
                    limit=limit_per_provider,
                )

                if results is None:
                    raise TypeError(
                        "Provider returned None instead of a candidate list."
                    )

                provider_result_counts[provider.provider_name] = len(results)

                for candidate in results:
                    if not isinstance(candidate, ComponentCandidate):
                        raise TypeError(
                            "Provider returned an item that is not a "
                            "ComponentCandidate."
                        )

                    if candidate.source_provider is None:
                        candidate = replace(
                            candidate,
                            source_provider=provider.provider_name,
                        )

                    raw_candidates.append(candidate)

            except Exception as exc:
                if stop_on_error:
                    raise

                failures.append(
                    ProviderFailure(
                        provider_name=provider.provider_name,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                provider_result_counts[provider.provider_name] = 0

        unique_candidates = self._merge_duplicate_candidates(raw_candidates)

        return ProviderSearchSummary(
            candidates=unique_candidates,
            failures=failures,
            provider_result_counts=provider_result_counts,
            total_raw_candidates=len(raw_candidates),
            total_unique_candidates=len(unique_candidates),
        )

    def _require_provider(self, provider_name: str) -> str:
        normalized = provider_name.strip().lower()

        if normalized not in self._enabled:
            raise KeyError(f"Unknown provider: {provider_name}")

        return normalized

    @staticmethod
    def _normalized_provider_name(
        provider: ComponentSearchProvider,
    ) -> str:
        name = provider.provider_name.strip().lower()

        if not name:
            raise ValueError("provider_name cannot be empty.")

        return name

    def _merge_duplicate_candidates(
        self,
        candidates: Iterable[ComponentCandidate],
    ) -> List[ComponentCandidate]:
        merged: Dict[Tuple[str, str], ComponentCandidate] = {}

        for candidate in candidates:
            key = self._candidate_key(candidate)

            if key not in merged:
                merged[key] = candidate
                continue

            merged[key] = self._merge_candidate_pair(
                merged[key],
                candidate,
            )

        return sorted(
            merged.values(),
            key=lambda item: (
                item.manufacturer.strip().lower(),
                item.part_number.strip().lower(),
            ),
        )

    @staticmethod
    def _candidate_key(
        candidate: ComponentCandidate,
    ) -> Tuple[str, str]:
        return (
            candidate.manufacturer.strip().lower(),
            candidate.part_number.strip().lower(),
        )

    def _merge_candidate_pair(
        self,
        first: ComponentCandidate,
        second: ComponentCandidate,
    ) -> ComponentCandidate:
        offers = self._merge_offers(first.offers, second.offers)

        source_names = self._merge_source_names(
            first.source_provider,
            second.source_provider,
        )

        extra = dict(first.extra)
        extra.update(second.extra)

        return ComponentCandidate(
            manufacturer=self._prefer_text(
                first.manufacturer,
                second.manufacturer,
            ),
            part_number=self._prefer_text(
                first.part_number,
                second.part_number,
            ),
            description=self._prefer_text(
                first.description,
                second.description,
            ),
            topology=self._prefer_text(
                first.topology,
                second.topology,
            ),
            lifecycle_status=self._prefer_lifecycle(
                first.lifecycle_status,
                second.lifecycle_status,
            ),
            input_voltage_min_v=self._prefer_number(
                first.input_voltage_min_v,
                second.input_voltage_min_v,
            ),
            input_voltage_max_v=self._prefer_number(
                first.input_voltage_max_v,
                second.input_voltage_max_v,
            ),
            output_voltage_min_v=self._prefer_number(
                first.output_voltage_min_v,
                second.output_voltage_min_v,
            ),
            output_voltage_max_v=self._prefer_number(
                first.output_voltage_max_v,
                second.output_voltage_max_v,
            ),
            output_current_max_a=self._prefer_number(
                first.output_current_max_a,
                second.output_current_max_a,
            ),
            switching_frequency_min_hz=self._prefer_number(
                first.switching_frequency_min_hz,
                second.switching_frequency_min_hz,
            ),
            switching_frequency_max_hz=self._prefer_number(
                first.switching_frequency_max_hz,
                second.switching_frequency_max_hz,
            ),
            typical_efficiency=self._prefer_number(
                first.typical_efficiency,
                second.typical_efficiency,
            ),
            synchronous_rectification=self._prefer_bool(
                first.synchronous_rectification,
                second.synchronous_rectification,
            ),
            integrated_switches=self._prefer_bool(
                first.integrated_switches,
                second.integrated_switches,
            ),
            package_name=self._prefer_optional_text(
                first.package_name,
                second.package_name,
            ),
            package_width_mm=self._prefer_number(
                first.package_width_mm,
                second.package_width_mm,
            ),
            package_length_mm=self._prefer_number(
                first.package_length_mm,
                second.package_length_mm,
            ),
            operating_temperature_min_c=self._prefer_number(
                first.operating_temperature_min_c,
                second.operating_temperature_min_c,
            ),
            operating_temperature_max_c=self._prefer_number(
                first.operating_temperature_max_c,
                second.operating_temperature_max_c,
            ),
            datasheet_url=self._prefer_optional_text(
                first.datasheet_url,
                second.datasheet_url,
            ),
            source_provider=source_names,
            offers=offers,
            extra=extra,
        )

    @staticmethod
    def _merge_offers(
        first: Iterable[DistributorOffer],
        second: Iterable[DistributorOffer],
    ) -> List[DistributorOffer]:
        merged: Dict[Tuple[str, str, str], DistributorOffer] = {}

        for offer in [*first, *second]:
            key = (
                offer.distributor.strip().lower(),
                (offer.sku or "").strip().lower(),
                offer.currency.strip().upper(),
            )

            existing = merged.get(key)
            if existing is None:
                merged[key] = offer
                continue

            merged[key] = ProviderManager._prefer_offer(
                existing,
                offer,
            )

        return sorted(
            merged.values(),
            key=lambda offer: (
                offer.distributor.strip().lower(),
                offer.unit_price
                if offer.unit_price is not None
                else float("inf"),
            ),
        )

    @staticmethod
    def _prefer_offer(
        first: DistributorOffer,
        second: DistributorOffer,
    ) -> DistributorOffer:
        first_stock = first.stock_quantity or 0
        second_stock = second.stock_quantity or 0

        if first.is_in_stock != second.is_in_stock:
            return first if first.is_in_stock else second

        if first.unit_price is None:
            return second
        if second.unit_price is None:
            return first

        if first.unit_price != second.unit_price:
            return first if first.unit_price < second.unit_price else second

        return first if first_stock >= second_stock else second

    @staticmethod
    def _merge_source_names(
        first: Optional[str],
        second: Optional[str],
    ) -> Optional[str]:
        names = []

        for value in (first, second):
            if not value:
                continue
            for name in value.split(","):
                cleaned = name.strip()
                if cleaned and cleaned.lower() not in {
                    existing.lower() for existing in names
                }:
                    names.append(cleaned)

        return ", ".join(names) if names else None

    @staticmethod
    def _prefer_text(first: str, second: str) -> str:
        return first if first.strip() else second

    @staticmethod
    def _prefer_optional_text(
        first: Optional[str],
        second: Optional[str],
    ) -> Optional[str]:
        return first if first not in (None, "") else second

    @staticmethod
    def _prefer_number(
        first: Optional[float],
        second: Optional[float],
    ) -> Optional[float]:
        return first if first is not None else second

    @staticmethod
    def _prefer_bool(
        first: Optional[bool],
        second: Optional[bool],
    ) -> Optional[bool]:
        return first if first is not None else second

    @staticmethod
    def _prefer_lifecycle(first, second):
        ranking = {
            "active": 4,
            "unknown": 3,
            "not_recommended_for_new_designs": 2,
            "obsolete": 1,
        }

        first_rank = ranking.get(first.value, 0)
        second_rank = ranking.get(second.value, 0)

        return first if first_rank >= second_rank else second
