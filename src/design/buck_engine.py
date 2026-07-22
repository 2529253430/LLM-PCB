from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Dict, List, Optional


class BuckDesignError(Exception):
    """Raised when Buck design inputs are invalid or physically inconsistent."""


@dataclass(frozen=True)
class BuckICParameters:
    """
    Electrical parameters of the selected Buck regulator.

    These values should come from a verified datasheet or normalized provider
    record. Missing values may be supplied manually during early development.
    """

    part_number: str
    feedback_reference_voltage_v: float
    switching_frequency_hz: float

    minimum_on_time_s: Optional[float] = None
    maximum_duty_cycle: Optional[float] = None
    switch_current_limit_a: Optional[float] = None

    high_side_rds_on_ohm: Optional[float] = None
    low_side_rds_on_ohm: Optional[float] = None
    diode_forward_voltage_v: Optional[float] = None

    synchronous_rectification: bool = True

    def validate(self) -> None:
        if not self.part_number.strip():
            raise BuckDesignError("part_number cannot be empty.")
        if self.feedback_reference_voltage_v <= 0:
            raise BuckDesignError(
                "feedback_reference_voltage_v must be greater than zero."
            )
        if self.switching_frequency_hz <= 0:
            raise BuckDesignError(
                "switching_frequency_hz must be greater than zero."
            )
        if (
            self.maximum_duty_cycle is not None
            and not 0 < self.maximum_duty_cycle <= 1
        ):
            raise BuckDesignError(
                "maximum_duty_cycle must be expressed as a ratio from 0 to 1."
            )
        if (
            self.minimum_on_time_s is not None
            and self.minimum_on_time_s <= 0
        ):
            raise BuckDesignError(
                "minimum_on_time_s must be greater than zero."
            )
        if (
            self.switch_current_limit_a is not None
            and self.switch_current_limit_a <= 0
        ):
            raise BuckDesignError(
                "switch_current_limit_a must be greater than zero."
            )


@dataclass(frozen=True)
class BuckDesignInput:
    """Target electrical requirements and design preferences."""

    input_voltage_min_v: float
    input_voltage_max_v: float
    output_voltage_v: float
    output_current_a: float

    inductor_ripple_ratio: float = 0.30
    output_voltage_ripple_v: float = 0.05
    input_voltage_ripple_v: float = 0.20

    feedback_bottom_resistance_ohm: float = 10_000.0

    inductor_value_tolerance_ratio: float = 0.20
    capacitor_derating_ratio: float = 0.50
    current_margin_ratio: float = 0.25
    voltage_margin_ratio: float = 0.25

    output_capacitor_esr_ohm: Optional[float] = None
    input_capacitor_esr_ohm: Optional[float] = None

    notes: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.input_voltage_min_v <= 0:
            raise BuckDesignError(
                "input_voltage_min_v must be greater than zero."
            )
        if self.input_voltage_max_v < self.input_voltage_min_v:
            raise BuckDesignError(
                "input_voltage_max_v must be greater than or equal to "
                "input_voltage_min_v."
            )
        if self.output_voltage_v <= 0:
            raise BuckDesignError(
                "output_voltage_v must be greater than zero."
            )
        if self.output_voltage_v >= self.input_voltage_min_v:
            raise BuckDesignError(
                "Buck output voltage must be lower than minimum input voltage."
            )
        if self.output_current_a <= 0:
            raise BuckDesignError(
                "output_current_a must be greater than zero."
            )
        if not 0 < self.inductor_ripple_ratio < 1:
            raise BuckDesignError(
                "inductor_ripple_ratio must be between 0 and 1."
            )
        if self.output_voltage_ripple_v <= 0:
            raise BuckDesignError(
                "output_voltage_ripple_v must be greater than zero."
            )
        if self.input_voltage_ripple_v <= 0:
            raise BuckDesignError(
                "input_voltage_ripple_v must be greater than zero."
            )
        if self.feedback_bottom_resistance_ohm <= 0:
            raise BuckDesignError(
                "feedback_bottom_resistance_ohm must be greater than zero."
            )
        if not 0 <= self.capacitor_derating_ratio < 1:
            raise BuckDesignError(
                "capacitor_derating_ratio must be from 0 up to but not "
                "including 1."
            )
        if self.current_margin_ratio < 0:
            raise BuckDesignError(
                "current_margin_ratio cannot be negative."
            )
        if self.voltage_margin_ratio < 0:
            raise BuckDesignError(
                "voltage_margin_ratio cannot be negative."
            )


@dataclass(frozen=True)
class BuckDesignResult:
    part_number: str

    duty_cycle_at_min_input: float
    duty_cycle_at_max_input: float

    target_inductor_ripple_a: float
    calculated_inductance_h: float
    recommended_inductance_h: float
    inductor_peak_current_a: float
    recommended_inductor_current_rating_a: float

    minimum_output_capacitance_f: float
    recommended_output_capacitance_f: float
    maximum_output_capacitor_esr_ohm: float

    minimum_input_capacitance_f: float
    recommended_input_capacitance_f: float
    input_capacitor_rms_current_a: float

    feedback_top_resistance_ohm: float
    feedback_bottom_resistance_ohm: float
    calculated_output_voltage_v: float

    recommended_input_capacitor_voltage_rating_v: float
    recommended_output_capacitor_voltage_rating_v: float

    estimated_output_power_w: float
    estimated_input_rms_current_a: float

    warnings: List[str]
    assumptions: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "part_number": self.part_number,
            "duty_cycle_at_min_input": self.duty_cycle_at_min_input,
            "duty_cycle_at_max_input": self.duty_cycle_at_max_input,
            "target_inductor_ripple_a": self.target_inductor_ripple_a,
            "calculated_inductance_h": self.calculated_inductance_h,
            "recommended_inductance_h": self.recommended_inductance_h,
            "inductor_peak_current_a": self.inductor_peak_current_a,
            "recommended_inductor_current_rating_a": (
                self.recommended_inductor_current_rating_a
            ),
            "minimum_output_capacitance_f": (
                self.minimum_output_capacitance_f
            ),
            "recommended_output_capacitance_f": (
                self.recommended_output_capacitance_f
            ),
            "maximum_output_capacitor_esr_ohm": (
                self.maximum_output_capacitor_esr_ohm
            ),
            "minimum_input_capacitance_f": (
                self.minimum_input_capacitance_f
            ),
            "recommended_input_capacitance_f": (
                self.recommended_input_capacitance_f
            ),
            "input_capacitor_rms_current_a": (
                self.input_capacitor_rms_current_a
            ),
            "feedback_top_resistance_ohm": (
                self.feedback_top_resistance_ohm
            ),
            "feedback_bottom_resistance_ohm": (
                self.feedback_bottom_resistance_ohm
            ),
            "calculated_output_voltage_v": (
                self.calculated_output_voltage_v
            ),
            "recommended_input_capacitor_voltage_rating_v": (
                self.recommended_input_capacitor_voltage_rating_v
            ),
            "recommended_output_capacitor_voltage_rating_v": (
                self.recommended_output_capacitor_voltage_rating_v
            ),
            "estimated_output_power_w": self.estimated_output_power_w,
            "estimated_input_rms_current_a": (
                self.estimated_input_rms_current_a
            ),
            "warnings": list(self.warnings),
            "assumptions": list(self.assumptions),
        }


class BuckDesignEngine:
    """
    Deterministic first-pass Buck peripheral component calculator.

    The engine intentionally uses conservative, transparent equations. It is a
    preliminary design tool, not a substitute for the selected IC datasheet,
    loop-compensation design, thermal analysis, simulation, or prototype test.
    """

    STANDARD_INDUCTORS_H = [
        0.47e-6,
        0.68e-6,
        1.0e-6,
        1.5e-6,
        2.2e-6,
        3.3e-6,
        4.7e-6,
        6.8e-6,
        10e-6,
        15e-6,
        22e-6,
        33e-6,
        47e-6,
        68e-6,
        100e-6,
        150e-6,
        220e-6,
    ]

    STANDARD_CAPACITORS_F = [
        0.1e-6,
        0.22e-6,
        0.47e-6,
        1.0e-6,
        2.2e-6,
        4.7e-6,
        10e-6,
        22e-6,
        47e-6,
        100e-6,
        220e-6,
        470e-6,
        1000e-6,
    ]

    def design(
        self,
        design_input: BuckDesignInput,
        ic: BuckICParameters,
    ) -> BuckDesignResult:
        design_input.validate()
        ic.validate()

        warnings: List[str] = []
        assumptions: List[str] = [
            "采用连续导通模式的一阶 Buck 近似模型。",
            "忽略 PCB 寄生参数、开关节点振铃和控制环动态影响。",
            "电容推荐值已经考虑用户指定的直流偏压降额比例。",
            "最终值必须结合芯片数据手册推荐范围重新核对。",
        ]

        duty_min_input = (
            design_input.output_voltage_v
            / design_input.input_voltage_min_v
        )
        duty_max_input = (
            design_input.output_voltage_v
            / design_input.input_voltage_max_v
        )

        self._check_duty_cycle(
            design_input,
            ic,
            duty_min_input,
            duty_max_input,
            warnings,
        )

        target_ripple = (
            design_input.output_current_a
            * design_input.inductor_ripple_ratio
        )

        inductance = self._calculate_inductance(
            vin=design_input.input_voltage_max_v,
            vout=design_input.output_voltage_v,
            ripple_current=target_ripple,
            switching_frequency=ic.switching_frequency_hz,
        )

        recommended_inductance = self._select_standard_value_up(
            inductance,
            self.STANDARD_INDUCTORS_H,
        )

        worst_case_inductance = (
            recommended_inductance
            * (1.0 - design_input.inductor_value_tolerance_ratio)
        )

        actual_ripple = self._calculate_ripple_current(
            vin=design_input.input_voltage_max_v,
            vout=design_input.output_voltage_v,
            inductance=worst_case_inductance,
            switching_frequency=ic.switching_frequency_hz,
        )

        peak_current = (
            design_input.output_current_a
            + actual_ripple / 2.0
        )

        recommended_current_rating = (
            peak_current
            * (1.0 + design_input.current_margin_ratio)
        )

        if (
            ic.switch_current_limit_a is not None
            and peak_current >= ic.switch_current_limit_a
        ):
            warnings.append(
                "计算得到的电感峰值电流达到或超过芯片开关限流值。"
            )

        max_esr = (
            design_input.output_voltage_ripple_v
            / actual_ripple
        )

        if design_input.output_capacitor_esr_ohm is not None:
            esr_ripple = (
                actual_ripple
                * design_input.output_capacitor_esr_ohm
            )
            capacitive_ripple_budget = (
                design_input.output_voltage_ripple_v
                - esr_ripple
            )

            if capacitive_ripple_budget <= 0:
                raise BuckDesignError(
                    "Specified output capacitor ESR alone exceeds the "
                    "allowed output ripple."
                )
        else:
            capacitive_ripple_budget = (
                design_input.output_voltage_ripple_v
            )

        minimum_cout = (
            actual_ripple
            / (
                8.0
                * ic.switching_frequency_hz
                * capacitive_ripple_budget
            )
        )

        recommended_cout = self._apply_capacitor_derating(
            minimum_cout,
            design_input.capacitor_derating_ratio,
        )
        recommended_cout = self._select_standard_value_up(
            recommended_cout,
            self.STANDARD_CAPACITORS_F,
        )

        duty_for_input_cap = duty_min_input

        minimum_cin = (
            design_input.output_current_a
            * duty_for_input_cap
            * (1.0 - duty_for_input_cap)
            / (
                ic.switching_frequency_hz
                * design_input.input_voltage_ripple_v
            )
        )

        recommended_cin = self._apply_capacitor_derating(
            minimum_cin,
            design_input.capacitor_derating_ratio,
        )
        recommended_cin = self._select_standard_value_up(
            recommended_cin,
            self.STANDARD_CAPACITORS_F,
        )

        cin_rms = (
            design_input.output_current_a
            * sqrt(
                duty_for_input_cap
                * (1.0 - duty_for_input_cap)
            )
        )

        r_bottom = design_input.feedback_bottom_resistance_ohm
        r_top = r_bottom * (
            design_input.output_voltage_v
            / ic.feedback_reference_voltage_v
            - 1.0
        )

        if r_top <= 0:
            raise BuckDesignError(
                "Feedback divider calculation produced a non-positive "
                "top resistance."
            )

        calculated_vout = (
            ic.feedback_reference_voltage_v
            * (1.0 + r_top / r_bottom)
        )

        input_voltage_rating = (
            design_input.input_voltage_max_v
            * (1.0 + design_input.voltage_margin_ratio)
        )
        output_voltage_rating = (
            design_input.output_voltage_v
            * (1.0 + design_input.voltage_margin_ratio)
        )

        output_power = (
            design_input.output_voltage_v
            * design_input.output_current_a
        )

        estimated_input_rms = (
            design_input.output_current_a
            * duty_for_input_cap
        )

        if design_input.inductor_ripple_ratio > 0.4:
            warnings.append(
                "电感纹波比例较高，可能增加峰值电流、输出纹波和 EMI。"
            )

        if design_input.capacitor_derating_ratio < 0.3:
            warnings.append(
                "电容降额比例较低，MLCC 直流偏压可能导致实际容量不足。"
            )

        return BuckDesignResult(
            part_number=ic.part_number,
            duty_cycle_at_min_input=duty_min_input,
            duty_cycle_at_max_input=duty_max_input,
            target_inductor_ripple_a=target_ripple,
            calculated_inductance_h=inductance,
            recommended_inductance_h=recommended_inductance,
            inductor_peak_current_a=peak_current,
            recommended_inductor_current_rating_a=(
                recommended_current_rating
            ),
            minimum_output_capacitance_f=minimum_cout,
            recommended_output_capacitance_f=recommended_cout,
            maximum_output_capacitor_esr_ohm=max_esr,
            minimum_input_capacitance_f=minimum_cin,
            recommended_input_capacitance_f=recommended_cin,
            input_capacitor_rms_current_a=cin_rms,
            feedback_top_resistance_ohm=r_top,
            feedback_bottom_resistance_ohm=r_bottom,
            calculated_output_voltage_v=calculated_vout,
            recommended_input_capacitor_voltage_rating_v=(
                input_voltage_rating
            ),
            recommended_output_capacitor_voltage_rating_v=(
                output_voltage_rating
            ),
            estimated_output_power_w=output_power,
            estimated_input_rms_current_a=estimated_input_rms,
            warnings=warnings,
            assumptions=assumptions,
        )

    @staticmethod
    def _calculate_inductance(
        vin: float,
        vout: float,
        ripple_current: float,
        switching_frequency: float,
    ) -> float:
        duty = vout / vin

        return (
            (vin - vout)
            * duty
            / (ripple_current * switching_frequency)
        )

    @staticmethod
    def _calculate_ripple_current(
        vin: float,
        vout: float,
        inductance: float,
        switching_frequency: float,
    ) -> float:
        duty = vout / vin

        return (
            (vin - vout)
            * duty
            / (inductance * switching_frequency)
        )

    @staticmethod
    def _apply_capacitor_derating(
        required_capacitance: float,
        derating_ratio: float,
    ) -> float:
        effective_fraction = 1.0 - derating_ratio
        return required_capacitance / effective_fraction

    @staticmethod
    def _select_standard_value_up(
        calculated_value: float,
        standard_values: List[float],
    ) -> float:
        for value in standard_values:
            if value >= calculated_value:
                return value

        return calculated_value

    @staticmethod
    def _check_duty_cycle(
        design_input: BuckDesignInput,
        ic: BuckICParameters,
        duty_at_min_input: float,
        duty_at_max_input: float,
        warnings: List[str],
    ) -> None:
        if (
            ic.maximum_duty_cycle is not None
            and duty_at_min_input > ic.maximum_duty_cycle
        ):
            raise BuckDesignError(
                "Required maximum duty cycle exceeds the IC limit."
            )

        if ic.minimum_on_time_s is not None:
            minimum_possible_duty = (
                ic.minimum_on_time_s
                * ic.switching_frequency_hz
            )

            if duty_at_max_input < minimum_possible_duty:
                warnings.append(
                    "最大输入电压下所需占空比低于芯片最小导通时间"
                    "对应的占空比，可能出现跳脉冲或输出调节问题。"
                )
