from __future__ import annotations

from pathlib import Path

from src.sourcing.comparator import BuckComponentComparator
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import BuckDesignRequirements
from src.sourcing.provider_manager import ProviderManager
from src.sourcing.report import ComponentComparisonReportBuilder


def main() -> None:
    requirements = BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=10,
        currency="USD",
        destination_country="SG",
        max_unit_price=6.0,
        require_in_stock=True,
        require_active_lifecycle=True,
    )

    manager = ProviderManager(
        [MockComponentSearchProvider()]
    )
    summary = manager.search_buck_regulators(requirements)

    comparator = BuckComponentComparator()
    results = comparator.compare(
        summary.candidates,
        requirements,
        include_rejected=True,
    )

    report = ComponentComparisonReportBuilder().build(
        requirements,
        results,
        top_count=5,
    )

    output_path = Path(
        "output/component_comparison_report.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        report.markdown,
        encoding="utf-8",
    )

    print(report.summary)
    print(report.recommendation or "No valid recommendation.")
    print(f"Report written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
