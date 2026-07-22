from __future__ import annotations

import pytest

from src.sourcing.failing_provider import (
    FailingComponentSearchProvider,
)
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import (
    BuckDesignRequirements,
    ComponentCandidate,
    DistributorOffer,
    LifecycleStatus,
)
from src.sourcing.provider import ComponentSearchProvider
from src.sourcing.provider_manager import ProviderManager


def _requirements() -> BuckDesignRequirements:
    return BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=10,
        currency="USD",
        max_unit_price=8.0,
    )


class DuplicateProvider(ComponentSearchProvider):
    @property
    def provider_name(self) -> str:
        return "duplicate"

    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit: int = 50,
    ):
        return [
            ComponentCandidate(
                manufacturer="Example Semiconductor",
                part_number="EXB-36V-4A",
                description="Duplicate record with another offer",
                lifecycle_status=LifecycleStatus.ACTIVE,
                input_voltage_max_v=36.0,
                output_voltage_min_v=0.8,
                output_voltage_max_v=30.0,
                output_current_max_a=4.0,
                typical_efficiency=0.93,
                package_name="QFN-16",
                package_width_mm=3.0,
                package_length_mm=3.0,
                source_provider=self.provider_name,
                offers=[
                    DistributorOffer(
                        distributor="Second Distributor",
                        sku="SECOND-001",
                        unit_price=2.50,
                        currency=requirements.currency,
                        stock_quantity=500,
                    )
                ],
            )
        ]


def test_manager_searches_registered_providers() -> None:
    manager = ProviderManager([MockComponentSearchProvider()])

    summary = manager.search_buck_regulators(_requirements())

    assert summary.total_raw_candidates == 3
    assert summary.total_unique_candidates == 3
    assert summary.failures == []
    assert summary.provider_result_counts["mock"] == 3


def test_manager_isolates_provider_failure() -> None:
    manager = ProviderManager(
        [
            FailingComponentSearchProvider(),
            MockComponentSearchProvider(),
        ]
    )

    summary = manager.search_buck_regulators(_requirements())

    assert summary.total_unique_candidates == 3
    assert len(summary.failures) == 1
    assert summary.failures[0].provider_name == "failing-provider"
    assert summary.provider_result_counts["failing-provider"] == 0


def test_manager_can_stop_on_error() -> None:
    manager = ProviderManager(
        [FailingComponentSearchProvider()]
    )

    with pytest.raises(RuntimeError, match="Simulated"):
        manager.search_buck_regulators(
            _requirements(),
            stop_on_error=True,
        )


def test_manager_merges_duplicate_candidates_and_offers() -> None:
    manager = ProviderManager(
        [
            MockComponentSearchProvider(),
            DuplicateProvider(),
        ]
    )

    summary = manager.search_buck_regulators(_requirements())

    assert summary.total_raw_candidates == 4
    assert summary.total_unique_candidates == 3

    candidate = next(
        item
        for item in summary.candidates
        if item.part_number == "EXB-36V-4A"
    )

    assert len(candidate.offers) == 2
    assert "mock" in candidate.source_provider
    assert "duplicate" in candidate.source_provider
    assert candidate.best_offer(10, "USD").unit_price == 2.50


def test_manager_can_disable_provider() -> None:
    manager = ProviderManager(
        [
            MockComponentSearchProvider(),
            DuplicateProvider(),
        ]
    )

    manager.disable("duplicate")
    summary = manager.search_buck_regulators(_requirements())

    assert summary.total_raw_candidates == 3
    assert "duplicate" not in summary.provider_result_counts


def test_duplicate_provider_names_are_rejected() -> None:
    manager = ProviderManager([MockComponentSearchProvider()])

    with pytest.raises(ValueError, match="already been registered"):
        manager.register(MockComponentSearchProvider())


def test_unknown_provider_raises_key_error() -> None:
    manager = ProviderManager()

    with pytest.raises(KeyError):
        manager.enable("missing")
