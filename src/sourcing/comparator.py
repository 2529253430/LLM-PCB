from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from .models import (
    BuckDesignRequirements,
    ComponentCandidate,
    EvaluationResult,
    LifecycleStatus,
)


class BuckComponentComparator:
    """
    Apply deterministic Buck suitability checks and rank valid candidates.

    The comparator deliberately contains no web-access logic. It receives
    normalized ComponentCandidate objects from one or more providers.
    """

    SCORE_MAX = 100.0

    def evaluate(
        self,
        candidate: ComponentCandidate,
        requirements: BuckDesignRequirements,
    ) -> EvaluationResult:
        requirements.validate()

        rejection_reasons: List[str] = []
        warnings: List[str] = []

        required_voltage_rating = (
            requirements.input_voltage_max_v
            * (1.0 + requirements.voltage_margin_ratio)
        )
        required_current_rating = (
            requirements.output_current_a
            * (1.0 + requirements.current_margin_ratio)
        )

        self._check_hard_constraints(
            candidate=candidate,
            requirements=requirements,
            required_voltage_rating=required_voltage_rating,
            required_current_rating=required_current_rating,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

        category_scores: Dict[str, float] = {}
        explanations: Dict[str, str] = {}

        category_scores["electrical_margin"], explanations["electrical_margin"] = (
            self._score_electrical_margin(
                candidate,
                required_voltage_rating,
                required_current_rating,
            )
        )

        best_offer = candidate.best_offer(
            requirements.quantity,
            requirements.currency,
        )

        category_scores["price"], explanations["price"] = self._score_price(
            best_offer.unit_price if best_offer else None,
            requirements.max_unit_price,
        )
        category_scores["stock"], explanations["stock"] = self._score_stock(
            best_offer.stock_quantity if best_offer else None,
            requirements.quantity,
        )
        category_scores["efficiency"], explanations["efficiency"] = (
            self._score_efficiency(
                candidate.typical_efficiency,
                requirements.minimum_efficiency,
            )
        )
        category_scores["package_area"], explanations["package_area"] = (
            self._score_package_area(
                candidate.package_area_mm2,
                requirements.maximum_package_area_mm2,
            )
        )
        category_scores["lifecycle"], explanations["lifecycle"] = (
            self._score_lifecycle(candidate.lifecycle_status)
        )
        category_scores["data_completeness"], explanations[
            "data_completeness"
        ] = self._score_data_completeness(candidate)

        total_score = self._weighted_total(
            category_scores,
            requirements.preference_weights,
        )

        if rejection_reasons:
            total_score = 0.0

        return EvaluationResult(
            candidate=candidate,
            passed_hard_constraints=not rejection_reasons,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            total_score=round(total_score, 2),
            category_scores={
                key: round(value, 2)
                for key, value in category_scores.items()
            },
            category_explanations=explanations,
            recommended_offer=best_offer,
        )

    def compare(
        self,
        candidates: Iterable[ComponentCandidate],
        requirements: BuckDesignRequirements,
        include_rejected: bool = False,
    ) -> List[EvaluationResult]:
        results = [
            self.evaluate(candidate, requirements)
            for candidate in candidates
        ]

        if not include_rejected:
            results = [
                result
                for result in results
                if result.passed_hard_constraints
            ]

        return sorted(
            results,
            key=lambda result: (
                result.passed_hard_constraints,
                result.total_score,
            ),
            reverse=True,
        )

    def _check_hard_constraints(
        self,
        candidate: ComponentCandidate,
        requirements: BuckDesignRequirements,
        required_voltage_rating: float,
        required_current_rating: float,
        rejection_reasons: List[str],
        warnings: List[str],
    ) -> None:
        if candidate.topology.strip().lower() != "buck":
            rejection_reasons.append("器件不是 Buck 稳压器。")

        if candidate.input_voltage_max_v is None:
            rejection_reasons.append("缺少最大输入电压数据。")
        elif candidate.input_voltage_max_v < required_voltage_rating:
            rejection_reasons.append(
                "最大输入电压裕量不足："
                f"需要至少 {required_voltage_rating:.2f} V，"
                f"器件仅支持 {candidate.input_voltage_max_v:.2f} V。"
            )

        if candidate.output_current_max_a is None:
            rejection_reasons.append("缺少最大输出电流数据。")
        elif candidate.output_current_max_a < required_current_rating:
            rejection_reasons.append(
                "最大输出电流裕量不足："
                f"需要至少 {required_current_rating:.2f} A，"
                f"器件仅支持 {candidate.output_current_max_a:.2f} A。"
            )

        if (
            candidate.output_voltage_min_v is not None
            and requirements.output_voltage_v
            < candidate.output_voltage_min_v
        ):
            rejection_reasons.append("目标输出电压低于器件允许范围。")

        if (
            candidate.output_voltage_max_v is not None
            and requirements.output_voltage_v
            > candidate.output_voltage_max_v
        ):
            rejection_reasons.append("目标输出电压高于器件允许范围。")

        if (
            requirements.require_active_lifecycle
            and candidate.lifecycle_status
            in {
                LifecycleStatus.OBSOLETE,
                LifecycleStatus.NOT_RECOMMENDED_FOR_NEW_DESIGNS,
            }
        ):
            rejection_reasons.append(
                f"器件生命周期状态为 {candidate.lifecycle_status.value}。"
            )

        if (
            requirements.require_synchronous_rectification is not None
            and candidate.synchronous_rectification
            is not requirements.require_synchronous_rectification
        ):
            rejection_reasons.append("同步整流特性不满足要求。")

        best_offer = candidate.best_offer(
            requirements.quantity,
            requirements.currency,
        )

        if requirements.require_in_stock:
            if best_offer is None or not best_offer.is_in_stock:
                rejection_reasons.append("指定采购数量下没有可用库存。")

        if requirements.max_unit_price is not None:
            if best_offer is None or best_offer.unit_price is None:
                rejection_reasons.append("缺少可比较的价格数据。")
            elif best_offer.unit_price > requirements.max_unit_price:
                rejection_reasons.append(
                    f"单价 {best_offer.unit_price:.2f} "
                    f"{best_offer.currency} 超过预算。"
                )

        if (
            requirements.minimum_efficiency is not None
            and candidate.typical_efficiency is not None
            and candidate.typical_efficiency
            < requirements.minimum_efficiency
        ):
            rejection_reasons.append("典型效率低于用户要求。")

        if candidate.typical_efficiency is None:
            warnings.append("缺少统一测试条件下的效率数据。")

        if candidate.package_area_mm2 is None:
            warnings.append("缺少封装尺寸，无法准确比较 PCB 占用面积。")

        if candidate.datasheet_url is None:
            warnings.append("缺少数据手册链接。")

    @staticmethod
    def _score_electrical_margin(
        candidate: ComponentCandidate,
        required_voltage: float,
        required_current: float,
    ) -> Tuple[float, str]:
        if (
            candidate.input_voltage_max_v is None
            or candidate.output_current_max_a is None
        ):
            return 0.0, "缺少电压或电流额定值。"

        voltage_ratio = candidate.input_voltage_max_v / required_voltage
        current_ratio = candidate.output_current_max_a / required_current

        limiting_ratio = min(voltage_ratio, current_ratio)
        score = max(0.0, min(100.0, 50.0 + 50.0 * (limiting_ratio - 1.0)))

        return score, (
            f"电压裕量比 {voltage_ratio:.2f}，"
            f"电流裕量比 {current_ratio:.2f}。"
        )

    @staticmethod
    def _score_price(
        unit_price: Optional[float],
        max_unit_price: Optional[float],
    ) -> Tuple[float, str]:
        if unit_price is None:
            return 0.0, "没有可用单价。"

        if max_unit_price is None:
            score = 70.0
            return score, f"单价为 {unit_price:.2f}，未设置价格上限。"

        ratio = unit_price / max_unit_price
        score = max(0.0, min(100.0, 100.0 * (1.0 - 0.8 * ratio)))
        return score, (
            f"单价占预算上限的 {ratio * 100.0:.1f}%。"
        )

    @staticmethod
    def _score_stock(
        stock_quantity: Optional[int],
        required_quantity: int,
    ) -> Tuple[float, str]:
        if stock_quantity is None:
            return 0.0, "库存未知。"
        if stock_quantity < required_quantity:
            return 0.0, "库存不足。"

        ratio = stock_quantity / required_quantity
        score = min(100.0, 50.0 + 10.0 * ratio)
        return score, (
            f"库存 {stock_quantity}，需求数量 {required_quantity}。"
        )

    @staticmethod
    def _score_efficiency(
        efficiency: Optional[float],
        minimum_efficiency: Optional[float],
    ) -> Tuple[float, str]:
        if efficiency is None:
            return 30.0, "没有统一测试条件下的典型效率。"

        score = max(0.0, min(100.0, efficiency * 100.0))
        if minimum_efficiency is None:
            return score, f"典型效率约为 {efficiency * 100.0:.1f}%。"

        return score, (
            f"典型效率约为 {efficiency * 100.0:.1f}%，"
            f"最低要求为 {minimum_efficiency * 100.0:.1f}%。"
        )

    @staticmethod
    def _score_package_area(
        area_mm2: Optional[float],
        maximum_area_mm2: Optional[float],
    ) -> Tuple[float, str]:
        if area_mm2 is None:
            return 20.0, "封装面积未知。"

        if maximum_area_mm2 is None:
            score = max(20.0, min(100.0, 100.0 - area_mm2))
            return score, f"封装面积约为 {area_mm2:.2f} mm²。"

        ratio = area_mm2 / maximum_area_mm2
        score = max(0.0, min(100.0, 100.0 * (1.0 - 0.7 * ratio)))
        return score, (
            f"封装面积占允许上限的 {ratio * 100.0:.1f}%。"
        )

    @staticmethod
    def _score_lifecycle(
        status: LifecycleStatus,
    ) -> Tuple[float, str]:
        scores = {
            LifecycleStatus.ACTIVE: 100.0,
            LifecycleStatus.UNKNOWN: 50.0,
            LifecycleStatus.NOT_RECOMMENDED_FOR_NEW_DESIGNS: 20.0,
            LifecycleStatus.OBSOLETE: 0.0,
        }
        return scores[status], f"生命周期状态：{status.value}。"

    @staticmethod
    def _score_data_completeness(
        candidate: ComponentCandidate,
    ) -> Tuple[float, str]:
        fields = [
            candidate.input_voltage_max_v,
            candidate.output_current_max_a,
            candidate.output_voltage_min_v,
            candidate.output_voltage_max_v,
            candidate.typical_efficiency,
            candidate.package_area_mm2,
            candidate.operating_temperature_min_c,
            candidate.operating_temperature_max_c,
            candidate.datasheet_url,
        ]

        available = sum(value is not None for value in fields)
        score = available / len(fields) * 100.0
        return score, (
            f"关键字段完整度为 {available}/{len(fields)}。"
        )

    @staticmethod
    def _weighted_total(
        category_scores: Dict[str, float],
        weights: Dict[str, float],
    ) -> float:
        active_weights = {
            name: weight
            for name, weight in weights.items()
            if weight > 0 and name in category_scores
        }

        denominator = sum(active_weights.values())
        if denominator <= 0:
            return 0.0

        numerator = sum(
            category_scores[name] * weight
            for name, weight in active_weights.items()
        )
        return numerator / denominator
