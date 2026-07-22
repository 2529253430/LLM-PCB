from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LifecycleStatus(str, Enum):
    ACTIVE = "active"
    NOT_RECOMMENDED_FOR_NEW_DESIGNS = "not_recommended_for_new_designs"
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BuckDesignRequirements:
    """
    Normalized electrical and purchasing requirements for a Buck design.

    All voltages are expressed in volts, current in amperes, frequency in hertz,
    money in the selected currency, and dimensions in millimetres.
    """

    input_voltage_min_v: float
    input_voltage_max_v: float
    output_voltage_v: float
    output_current_a: float

    quantity: int = 1
    currency: str = "USD"
    destination_country: Optional[str] = None

    max_unit_price: Optional[float] = None
    preferred_switching_frequency_hz: Optional[float] = None
    minimum_efficiency: Optional[float] = None
    maximum_package_area_mm2: Optional[float] = None
    minimum_operating_temperature_c: Optional[float] = None
    maximum_operating_temperature_c: Optional[float] = None

    require_in_stock: bool = True
    require_active_lifecycle: bool = True
    require_synchronous_rectification: Optional[bool] = None

    voltage_margin_ratio: float = 0.20
    current_margin_ratio: float = 0.20

    preference_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "electrical_margin": 0.25,
            "price": 0.20,
            "stock": 0.15,
            "efficiency": 0.15,
            "package_area": 0.10,
            "lifecycle": 0.10,
            "data_completeness": 0.05,
        }
    )

    def validate(self) -> None:
        if self.input_voltage_min_v <= 0:
            raise ValueError("input_voltage_min_v must be greater than zero.")
        if self.input_voltage_max_v < self.input_voltage_min_v:
            raise ValueError(
                "input_voltage_max_v must be greater than or equal to "
                "input_voltage_min_v."
            )
        if self.output_voltage_v <= 0:
            raise ValueError("output_voltage_v must be greater than zero.")
        if self.output_voltage_v >= self.input_voltage_min_v:
            raise ValueError(
                "A Buck converter requires output_voltage_v to be lower than "
                "input_voltage_min_v."
            )
        if self.output_current_a <= 0:
            raise ValueError("output_current_a must be greater than zero.")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero.")
        if self.minimum_efficiency is not None:
            if not 0 < self.minimum_efficiency <= 1:
                raise ValueError(
                    "minimum_efficiency must be expressed as a ratio from 0 to 1."
                )
        if self.voltage_margin_ratio < 0 or self.current_margin_ratio < 0:
            raise ValueError("Safety margin ratios cannot be negative.")

        weight_total = sum(self.preference_weights.values())
        if weight_total <= 0:
            raise ValueError("At least one preference weight must be positive.")

        for name, weight in self.preference_weights.items():
            if weight < 0:
                raise ValueError(
                    f"Preference weight '{name}' cannot be negative."
                )


@dataclass(frozen=True)
class DistributorOffer:
    distributor: str
    sku: Optional[str]
    unit_price: Optional[float]
    currency: str
    stock_quantity: Optional[int]
    minimum_order_quantity: int = 1
    lead_time_days: Optional[int] = None
    product_url: Optional[str] = None
    last_updated_iso: Optional[str] = None

    @property
    def is_in_stock(self) -> bool:
        return (
            self.stock_quantity is not None
            and self.stock_quantity >= self.minimum_order_quantity
        )


@dataclass(frozen=True)
class ComponentCandidate:
    manufacturer: str
    part_number: str
    description: str

    topology: str = "buck"
    lifecycle_status: LifecycleStatus = LifecycleStatus.UNKNOWN

    input_voltage_min_v: Optional[float] = None
    input_voltage_max_v: Optional[float] = None
    output_voltage_min_v: Optional[float] = None
    output_voltage_max_v: Optional[float] = None
    output_current_max_a: Optional[float] = None

    switching_frequency_min_hz: Optional[float] = None
    switching_frequency_max_hz: Optional[float] = None
    typical_efficiency: Optional[float] = None

    synchronous_rectification: Optional[bool] = None
    integrated_switches: Optional[bool] = None

    package_name: Optional[str] = None
    package_width_mm: Optional[float] = None
    package_length_mm: Optional[float] = None

    operating_temperature_min_c: Optional[float] = None
    operating_temperature_max_c: Optional[float] = None

    datasheet_url: Optional[str] = None
    source_provider: Optional[str] = None
    offers: List[DistributorOffer] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def package_area_mm2(self) -> Optional[float]:
        if self.package_width_mm is None or self.package_length_mm is None:
            return None
        return self.package_width_mm * self.package_length_mm

    def best_offer(
        self,
        quantity: int,
        currency: Optional[str] = None,
    ) -> Optional[DistributorOffer]:
        valid = [
            offer
            for offer in self.offers
            if offer.minimum_order_quantity <= quantity
            and offer.unit_price is not None
            and (currency is None or offer.currency.upper() == currency.upper())
        ]

        if not valid:
            return None

        in_stock = [offer for offer in valid if offer.is_in_stock]
        pool = in_stock if in_stock else valid
        return min(pool, key=lambda offer: float(offer.unit_price))


@dataclass(frozen=True)
class EvaluationResult:
    candidate: ComponentCandidate
    passed_hard_constraints: bool
    rejection_reasons: List[str]
    warnings: List[str]

    total_score: float
    category_scores: Dict[str, float]
    category_explanations: Dict[str, str]

    recommended_offer: Optional[DistributorOffer] = None

    @property
    def part_number(self) -> str:
        return self.candidate.part_number
