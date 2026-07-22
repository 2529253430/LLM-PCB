from __future__ import annotations

from src.sourcing.comparator import BuckComponentComparator
from src.sourcing.mock_provider import MockComponentSearchProvider
from src.sourcing.models import BuckDesignRequirements
from src.sourcing.report import ComponentComparisonReportBuilder


def _requirements() -> BuckDesignRequirements:
    return BuckDesignRequirements(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        quantity=10,
        currency="USD",
        destination_country="SG",
        max_unit_price=6.0,
        require_in_stock=True,
    )


def _results():
    requirements = _requirements()
    provider = MockComponentSearchProvider()
    comparator = BuckComponentComparator()

    candidates = provider.search_buck_regulators(requirements)

    return requirements, comparator.compare(
        candidates,
        requirements,
        include_rejected=True,
    )


def test_report_contains_summary_and_recommendation() -> None:
    requirements, results = _results()

    report = ComponentComparisonReportBuilder().build(
        requirements,
        results,
    )

    assert report.valid_count == 2
    assert report.rejected_count == 1
    assert report.recommendation is not None
    assert "当前推荐" in report.recommendation
    assert "共评估 3 个候选器件" in report.summary


def test_report_contains_valid_and_rejected_sections() -> None:
    requirements, results = _results()

    report = ComponentComparisonReportBuilder().build(
        requirements,
        results,
    )

    assert "## 有效候选方案" in report.markdown
    assert "## 被淘汰的方案" in report.markdown
    assert "EXB-36V-4A" in report.markdown
    assert "EXB-28V-3A" in report.markdown
    assert "最大输入电压裕量不足" in report.markdown


def test_report_contains_data_limitations() -> None:
    requirements, results = _results()

    report = ComponentComparisonReportBuilder().build(
        requirements,
        results,
    )

    assert "数据可信度说明" in report.markdown
    assert "正式下单前必须重新查询" in report.markdown
    assert "不能替代数据手册曲线" in report.markdown


def test_top_count_limits_valid_candidate_details() -> None:
    requirements, results = _results()

    report = ComponentComparisonReportBuilder().build(
        requirements,
        results,
        top_count=1,
    )

    assert "### 1." in report.markdown
    assert "### 2." not in report.markdown


def test_invalid_top_count_is_rejected() -> None:
    requirements, results = _results()

    try:
        ComponentComparisonReportBuilder().build(
            requirements,
            results,
            top_count=0,
        )
    except ValueError as exc:
        assert "top_count" in str(exc)
    else:
        raise AssertionError("Expected ValueError.")
