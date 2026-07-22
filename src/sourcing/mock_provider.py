from __future__ import annotations

from typing import List

from .models import (
    BuckDesignRequirements,
    ComponentCandidate,
    DistributorOffer,
    LifecycleStatus,
)
from .provider import ComponentSearchProvider


class MockComponentSearchProvider(ComponentSearchProvider):
    """
    Offline provider used for development and tests.

    It imitates normalized data returned by future DigiKey, Mouser, or Nexar
    provider implementations without requiring credentials or internet access.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def search_buck_regulators(
        self,
        requirements: BuckDesignRequirements,
        limit: int = 50,
    ) -> List[ComponentCandidate]:
        candidates = [
            ComponentCandidate(
                manufacturer="Example Semiconductor",
                part_number="EXB-36V-4A",
                description="36 V, 4 A synchronous Buck regulator",
                lifecycle_status=LifecycleStatus.ACTIVE,
                input_voltage_min_v=4.5,
                input_voltage_max_v=36.0,
                output_voltage_min_v=0.8,
                output_voltage_max_v=30.0,
                output_current_max_a=4.0,
                switching_frequency_min_hz=200_000,
                switching_frequency_max_hz=1_200_000,
                typical_efficiency=0.93,
                synchronous_rectification=True,
                integrated_switches=True,
                package_name="QFN-16",
                package_width_mm=3.0,
                package_length_mm=3.0,
                operating_temperature_min_c=-40.0,
                operating_temperature_max_c=125.0,
                datasheet_url="https://example.invalid/EXB-36V-4A.pdf",
                source_provider=self.provider_name,
                offers=[
                    DistributorOffer(
                        distributor="Example Distributor",
                        sku="EXB-36V-4A-001",
                        unit_price=2.80,
                        currency=requirements.currency,
                        stock_quantity=1250,
                    )
                ],
            ),
            ComponentCandidate(
                manufacturer="Example Semiconductor",
                part_number="EXB-28V-3A",
                description="28 V, 3 A low-cost Buck regulator",
                lifecycle_status=LifecycleStatus.ACTIVE,
                input_voltage_min_v=4.5,
                input_voltage_max_v=28.0,
                output_voltage_min_v=0.8,
                output_voltage_max_v=24.0,
                output_current_max_a=3.0,
                switching_frequency_min_hz=500_000,
                switching_frequency_max_hz=500_000,
                typical_efficiency=0.89,
                synchronous_rectification=False,
                integrated_switches=True,
                package_name="SOIC-8",
                package_width_mm=3.9,
                package_length_mm=4.9,
                operating_temperature_min_c=-40.0,
                operating_temperature_max_c=125.0,
                datasheet_url="https://example.invalid/EXB-28V-3A.pdf",
                source_provider=self.provider_name,
                offers=[
                    DistributorOffer(
                        distributor="Example Distributor",
                        sku="EXB-28V-3A-001",
                        unit_price=1.20,
                        currency=requirements.currency,
                        stock_quantity=80,
                    )
                ],
            ),
            ComponentCandidate(
                manufacturer="Example Semiconductor",
                part_number="EXB-60V-5A",
                description="60 V, 5 A high-voltage Buck regulator",
                lifecycle_status=LifecycleStatus.ACTIVE,
                input_voltage_min_v=5.0,
                input_voltage_max_v=60.0,
                output_voltage_min_v=0.8,
                output_voltage_max_v=55.0,
                output_current_max_a=5.0,
                switching_frequency_min_hz=100_000,
                switching_frequency_max_hz=1_000_000,
                typical_efficiency=0.91,
                synchronous_rectification=True,
                integrated_switches=True,
                package_name="QFN-20",
                package_width_mm=4.0,
                package_length_mm=4.0,
                operating_temperature_min_c=-40.0,
                operating_temperature_max_c=150.0,
                datasheet_url="https://example.invalid/EXB-60V-5A.pdf",
                source_provider=self.provider_name,
                offers=[
                    DistributorOffer(
                        distributor="Example Distributor",
                        sku="EXB-60V-5A-001",
                        unit_price=5.60,
                        currency=requirements.currency,
                        stock_quantity=400,
                    )
                ],
            ),
        ]

        return candidates[:limit]
