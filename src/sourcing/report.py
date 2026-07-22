from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .models import BuckDesignRequirements, EvaluationResult


@dataclass(frozen=True)
class ComparisonReport:
    """User-facing comparison report generated from deterministic results."""

    title: str
    summary: str
    recommendation: Optional[str]
    markdown: str
    valid_count: int
    rejected_count: int


class ComponentComparisonReportBuilder:
    """
    Convert deterministic component evaluations into a readable report.

    This class does not perform electrical calculations or invent missing
    performance data. It only explains EvaluationResult objects produced by
    BuckComponentComparator.
    """

    DEFAULT_TOP_COUNT = 5

    def build(
        self,
        requirements: BuckDesignRequirements,
        results: Sequence[EvaluationResult],
        top_count: int = DEFAULT_TOP_COUNT,
    ) -> ComparisonReport:
        requirements.validate()

        if top_count <= 0:
            raise ValueError("top_count must be greater than zero.")

        valid_results = [
            result
            for result in results
            if result.passed_hard_constraints
        ]
        rejected_results = [
            result
            for result in results
            if not result.passed_hard_constraints
        ]

        valid_results = sorted(
            valid_results,
            key=lambda result: result.total_score,
            reverse=True,
        )
        rejected_results = sorted(
            rejected_results,
            key=lambda result: result.part_number.lower(),
        )

        recommendation = self._recommendation_text(valid_results)
        summary = self._summary_text(
            valid_count=len(valid_results),
            rejected_count=len(rejected_results),
        )

        markdown = self._build_markdown(
            requirements=requirements,
            valid_results=valid_results[:top_count],
            rejected_results=rejected_results,
            summary=summary,
            recommendation=recommendation,
        )

        return ComparisonReport(
            title="Buck 器件方案比较报告",
            summary=summary,
            recommendation=recommendation,
            markdown=markdown,
            valid_count=len(valid_results),
            rejected_count=len(rejected_results),
        )

    @staticmethod
    def _summary_text(
        valid_count: int,
        rejected_count: int,
    ) -> str:
        return (
            f"共评估 {valid_count + rejected_count} 个候选器件，"
            f"其中 {valid_count} 个满足硬性约束，"
            f"{rejected_count} 个被淘汰。"
        )

    def _recommendation_text(
        self,
        valid_results: Sequence[EvaluationResult],
    ) -> Optional[str]:
        if not valid_results:
            return None

        best = valid_results[0]
        candidate = best.candidate

        advantages = self._top_advantages(best, limit=3)
        advantage_text = "；".join(advantages)

        if advantage_text:
            return (
                f"当前推荐 {candidate.manufacturer} "
                f"{candidate.part_number}，综合评分 "
                f"{best.total_score:.2f}/100。主要原因："
                f"{advantage_text}。"
            )

        return (
            f"当前推荐 {candidate.manufacturer} "
            f"{candidate.part_number}，综合评分 "
            f"{best.total_score:.2f}/100。"
        )

    def _build_markdown(
        self,
        requirements: BuckDesignRequirements,
        valid_results: Sequence[EvaluationResult],
        rejected_results: Sequence[EvaluationResult],
        summary: str,
        recommendation: Optional[str],
    ) -> str:
        lines: List[str] = [
            "# Buck 器件方案比较报告",
            "",
            "## 设计需求",
            "",
            f"- 输入电压：{requirements.input_voltage_min_v:g}–"
            f"{requirements.input_voltage_max_v:g} V",
            f"- 输出电压：{requirements.output_voltage_v:g} V",
            f"- 输出电流：{requirements.output_current_a:g} A",
            f"- 采购数量：{requirements.quantity}",
            f"- 目标币种：{requirements.currency}",
        ]

        if requirements.destination_country:
            lines.append(
                f"- 采购地区：{requirements.destination_country}"
            )

        if requirements.max_unit_price is not None:
            lines.append(
                f"- 芯片单价上限："
                f"{requirements.max_unit_price:g} "
                f"{requirements.currency}"
            )

        lines.extend(
            [
                f"- 输入耐压安全裕量："
                f"{requirements.voltage_margin_ratio * 100:g}%",
                f"- 输出电流安全裕量："
                f"{requirements.current_margin_ratio * 100:g}%",
                "",
                "## 评估摘要",
                "",
                summary,
                "",
            ]
        )

        if recommendation:
            lines.extend(
                [
                    "## 推荐结论",
                    "",
                    recommendation,
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "## 推荐结论",
                    "",
                    "当前没有满足全部硬性约束的候选器件。"
                    "需要放宽约束、增加供应商来源，"
                    "或扩大器件搜索范围。",
                    "",
                ]
            )

        if valid_results:
            lines.extend(
                [
                    "## 有效候选方案",
                    "",
                    "| 排名 | 器件 | 综合评分 | 单价 | 库存 | "
                    "典型效率 | 封装 |",
                    "|---:|---|---:|---:|---:|---:|---|",
                ]
            )

            for index, result in enumerate(valid_results, start=1):
                candidate = result.candidate
                offer = result.recommended_offer

                price = (
                    f"{offer.unit_price:.2f} {offer.currency}"
                    if offer is not None
                    and offer.unit_price is not None
                    else "未知"
                )
                stock = (
                    str(offer.stock_quantity)
                    if offer is not None
                    and offer.stock_quantity is not None
                    else "未知"
                )
                efficiency = (
                    f"{candidate.typical_efficiency * 100:.1f}%"
                    if candidate.typical_efficiency is not None
                    else "未知"
                )
                package = candidate.package_name or "未知"

                lines.append(
                    f"| {index} | {candidate.manufacturer} "
                    f"{candidate.part_number} | "
                    f"{result.total_score:.2f} | {price} | "
                    f"{stock} | {efficiency} | {package} |"
                )

            lines.append("")

            for index, result in enumerate(valid_results, start=1):
                lines.extend(
                    self._candidate_detail_lines(index, result)
                )

        if rejected_results:
            lines.extend(
                [
                    "## 被淘汰的方案",
                    "",
                ]
            )

            for result in rejected_results:
                lines.append(
                    f"### {result.candidate.manufacturer} "
                    f"{result.part_number}"
                )
                lines.append("")

                for reason in result.rejection_reasons:
                    lines.append(f"- {reason}")

                if not result.rejection_reasons:
                    lines.append("- 未记录具体淘汰原因。")

                lines.append("")

        lines.extend(
            [
                "## 数据可信度说明",
                "",
                "- 排名仅基于当前获取到的结构化参数、"
                "价格、库存和评分权重。",
                "- “典型效率”只有在数据源提供明确数值时"
                "才参与直接比较。",
                "- 不同厂商的效率数据可能来自不同测试条件，"
                "不能替代数据手册曲线和样机测试。",
                "- 库存和价格具有时效性，正式下单前必须重新查询。",
                "- 最终器件仍需经过外围参数计算、热设计、"
                "稳定性分析和工程验证。",
                "",
            ]
        )

        return "\n".join(lines)

    def _candidate_detail_lines(
        self,
        rank: int,
        result: EvaluationResult,
    ) -> List[str]:
        candidate = result.candidate
        offer = result.recommended_offer

        lines = [
            f"### {rank}. {candidate.manufacturer} "
            f"{candidate.part_number}",
            "",
            f"**综合评分：{result.total_score:.2f}/100**",
            "",
        ]

        advantages = self._top_advantages(result, limit=4)
        risks = self._risks(result)

        if advantages:
            lines.append("**主要优势**")
            lines.append("")
            for item in advantages:
                lines.append(f"- {item}")
            lines.append("")

        if risks:
            lines.append("**风险与不足**")
            lines.append("")
            for item in risks:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("**分类评分**")
        lines.append("")

        for category, score in sorted(
            result.category_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            explanation = result.category_explanations.get(
                category,
                "",
            )
            name = self._category_name(category)
            lines.append(
                f"- {name}：{score:.2f}/100。{explanation}"
            )

        lines.append("")

        if offer is not None:
            lines.append("**推荐采购报价**")
            lines.append("")
            lines.append(
                f"- 供应商：{offer.distributor}"
            )
            lines.append(
                f"- SKU：{offer.sku or '未知'}"
            )
            lines.append(
                f"- 单价："
                f"{offer.unit_price if offer.unit_price is not None else '未知'} "
                f"{offer.currency}"
            )
            lines.append(
                f"- 库存："
                f"{offer.stock_quantity if offer.stock_quantity is not None else '未知'}"
            )
            lines.append(
                f"- 最小起订量：{offer.minimum_order_quantity}"
            )
            lines.append("")

        return lines

    def _top_advantages(
        self,
        result: EvaluationResult,
        limit: int,
    ) -> List[str]:
        sorted_scores = sorted(
            result.category_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        advantages: List[str] = []

        for category, score in sorted_scores:
            if score < 65:
                continue

            explanation = result.category_explanations.get(
                category,
                "",
            )
            name = self._category_name(category)

            if explanation:
                advantages.append(f"{name}较好（{explanation}）")
            else:
                advantages.append(f"{name}得分较高")

            if len(advantages) >= limit:
                break

        return advantages

    def _risks(
        self,
        result: EvaluationResult,
    ) -> List[str]:
        risks = list(result.warnings)

        for category, score in result.category_scores.items():
            if score >= 50:
                continue

            explanation = result.category_explanations.get(
                category,
                "",
            )
            name = self._category_name(category)

            risk = (
                f"{name}得分偏低：{explanation}"
                if explanation
                else f"{name}得分偏低。"
            )

            if risk not in risks:
                risks.append(risk)

        return risks

    @staticmethod
    def _category_name(category: str) -> str:
        names = {
            "electrical_margin": "电气裕量",
            "price": "价格",
            "stock": "库存",
            "efficiency": "效率",
            "package_area": "封装面积",
            "lifecycle": "生命周期",
            "data_completeness": "数据完整度",
        }
        return names.get(category, category)
