from __future__ import annotations

from src.sourcing.comparator import BuckComponentComparator
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import BuckDesignRequirements


def _requirements() -> BuckDesignRequirements:
    return BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=10,
        currency="USD",
        max_unit_price=6.0,
        require_in_stock=True,
        require_active_lifecycle=True,
    )


def test_mock_provider_returns_candidates() -> None:
    requirements = _requirements()
    provider = MockComponentSearchProvider()

    candidates = provider.search_buck_regulators(requirements)

    assert len(candidates) == 3
    assert all(candidate.topology == "buck" for candidate in candidates)


def test_comparator_rejects_insufficient_ratings() -> None:
    requirements = _requirements()
    provider = MockComponentSearchProvider()
    comparator = BuckComponentComparator()

    candidates = provider.search_buck_regulators(requirements)
    results = comparator.compare(
        candidates,
        requirements,
        include_rejected=True,
    )

    low_cost = next(
        result
        for result in results
        if result.part_number == "EXB-28V-3A"
    )

    assert low_cost.passed_hard_constraints is False
    assert low_cost.total_score == 0.0
    assert low_cost.rejection_reasons


def test_comparator_ranks_valid_candidates() -> None:
    requirements = _requirements()
    provider = MockComponentSearchProvider()
    comparator = BuckComponentComparator()

    candidates = provider.search_buck_regulators(requirements)
    results = comparator.compare(candidates, requirements)

    assert len(results) == 2
    assert all(result.passed_hard_constraints for result in results)
    assert results[0].total_score >= results[1].total_score


def test_evaluation_contains_explanations() -> None:
    requirements = _requirements()
    provider = MockComponentSearchProvider()
    comparator = BuckComponentComparator()

    candidate = provider.search_buck_regulators(requirements)[0]
    result = comparator.evaluate(candidate, requirements)

    assert "electrical_margin" in result.category_scores
    assert "price" in result.category_scores
    assert "stock" in result.category_scores
    assert result.category_explanations
    assert result.recommended_offer is not None
