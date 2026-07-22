from src.sourcing.comparator import BuckComponentComparator
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import BuckDesignRequirements


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

    provider = MockComponentSearchProvider()
    comparator = BuckComponentComparator()

    candidates = provider.search_buck_regulators(requirements)
    results = comparator.compare(
        candidates,
        requirements,
        include_rejected=True,
    )

    for index, result in enumerate(results, start=1):
        print(
            f"{index}. {result.candidate.manufacturer} "
            f"{result.part_number}"
        )
        print(f"   Passed: {result.passed_hard_constraints}")
        print(f"   Score: {result.total_score:.2f}")

        if result.recommended_offer is not None:
            offer = result.recommended_offer
            print(
                f"   Offer: {offer.distributor}, "
                f"{offer.unit_price} {offer.currency}, "
                f"stock={offer.stock_quantity}"
            )

        if result.rejection_reasons:
            print("   Rejection reasons:")
            for reason in result.rejection_reasons:
                print(f"   - {reason}")

        if result.warnings:
            print("   Warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")

        print("   Category scores:")
        for category, score in result.category_scores.items():
            explanation = result.category_explanations[category]
            print(f"   - {category}: {score:.2f} ({explanation})")

        print()


if __name__ == "__main__":
    main()
