from src.sourcing.comparator import BuckComponentComparator
from src.sourcing.failing_provider import (
    FailingComponentSearchProvider,
)
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import BuckDesignRequirements
from src.sourcing.provider_manager import ProviderManager


def main() -> None:
    requirements = BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=10,
        currency="USD",
        max_unit_price=6.0,
        require_in_stock=True,
    )

    manager = ProviderManager(
        [
            MockComponentSearchProvider(),
            FailingComponentSearchProvider(
                name="offline-demo-provider",
            ),
        ]
    )

    summary = manager.search_buck_regulators(requirements)

    print("Search summary")
    print(f"- Raw candidates: {summary.total_raw_candidates}")
    print(f"- Unique candidates: {summary.total_unique_candidates}")
    print(f"- Provider counts: {summary.provider_result_counts}")

    if summary.failures:
        print("- Provider failures:")
        for failure in summary.failures:
            print(
                f"  - {failure.provider_name}: "
                f"{failure.error_type}: {failure.message}"
            )

    comparator = BuckComponentComparator()
    results = comparator.compare(
        summary.candidates,
        requirements,
        include_rejected=True,
    )

    print()
    print("Comparison results")

    for index, result in enumerate(results, start=1):
        status = (
            "VALID"
            if result.passed_hard_constraints
            else "REJECTED"
        )

        print(
            f"{index}. {result.part_number}: "
            f"{status}, score={result.total_score:.2f}"
        )

        if result.recommended_offer is not None:
            offer = result.recommended_offer
            print(
                f"   Best offer: {offer.distributor}, "
                f"{offer.unit_price} {offer.currency}, "
                f"stock={offer.stock_quantity}"
            )

        for reason in result.rejection_reasons:
            print(f"   Reject: {reason}")


if __name__ == "__main__":
    main()
