"""Go/No-Go decision engine — engine #2."""

from __future__ import annotations

from dataclasses import dataclass

from api.schemas.analytics import GoNoGoFactors, GoNoGoResult
from api.utils.stats import clamp


@dataclass
class GoNoGoInput:
    estimated_award_value: float
    expected_competitors: int
    expected_margin_pct: float
    rawasi_capacity_load_pct: float
    relationship_with_entity: str = "neutral"
    sector_strategic_priority: str = "medium"
    project_duration_days: int | None = None
    payment_terms_score: float = 0.5
    item_overlap_with_capacity_pct: float = 0.5
    requires_new_classification: bool = False


WEIGHTS = {
    "win_probability": 0.30,
    "expected_margin": 0.25,
    "strategic_value": 0.15,
    "capacity_match": 0.10,
    "effort_required": 0.10,
    "cash_flow_impact": 0.10,
}


def _normalize_margin(margin_pct: float) -> float:
    return clamp(margin_pct / 15.0, 0.0, 1.0)


def _strategic_value_score(input_: GoNoGoInput) -> float:
    relationship_map = {"strong": 1.0, "good": 0.8, "neutral": 0.5, "weak": 0.3, "none": 0.1}
    priority_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
    rel = relationship_map.get(input_.relationship_with_entity, 0.5)
    pri = priority_map.get(input_.sector_strategic_priority, 0.6)
    return clamp(0.5 * rel + 0.5 * pri, 0.0, 1.0)


def _capacity_score(input_: GoNoGoInput) -> float:
    load_penalty = clamp(input_.rawasi_capacity_load_pct / 100, 0.0, 1.0)
    base = 0.5 + 0.5 * input_.item_overlap_with_capacity_pct
    if input_.requires_new_classification:
        base *= 0.5
    return clamp(base * (1 - 0.4 * load_penalty), 0.0, 1.0)


def _effort_score(input_: GoNoGoInput) -> float:
    """Returns higher = less effort required = better."""
    base = 1.0
    if input_.requires_new_classification:
        base -= 0.3
    if input_.estimated_award_value > 10_000_000:
        base -= 0.2
    return clamp(base, 0.0, 1.0)


class GoNoGoEngine:
    """Engine #2: composite decision score for entering a tender."""

    def evaluate(self, input_: GoNoGoInput, win_probability: float) -> GoNoGoResult:
        win_score = clamp(win_probability, 0.0, 1.0)
        margin_score = _normalize_margin(input_.expected_margin_pct)
        strategic = _strategic_value_score(input_)
        capacity = _capacity_score(input_)
        effort = _effort_score(input_)
        cashflow = clamp(input_.payment_terms_score, 0.0, 1.0)

        factors = GoNoGoFactors(
            win_probability=win_score,
            expected_margin=margin_score,
            strategic_value=strategic,
            capacity_match=capacity,
            effort_required=effort,
            cash_flow_impact=cashflow,
        )

        composite = (
            win_score * WEIGHTS["win_probability"]
            + margin_score * WEIGHTS["expected_margin"]
            + strategic * WEIGHTS["strategic_value"]
            + capacity * WEIGHTS["capacity_match"]
            + effort * WEIGHTS["effort_required"]
            + cashflow * WEIGHTS["cash_flow_impact"]
        )

        if composite >= 0.65:
            recommendation = "GO"
            confidence = "high" if composite >= 0.75 else "medium"
        elif composite >= 0.45:
            recommendation = "REVIEW"
            confidence = "medium"
        else:
            recommendation = "NO_GO"
            confidence = "high" if composite <= 0.30 else "medium"

        concerns, strengths = self._concerns_and_strengths(factors)
        reasoning = self._reasoning(recommendation, factors, input_)

        return GoNoGoResult(
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            composite_score=composite,
            factor_scores=factors,
            reasoning=reasoning,
            top_concerns=concerns,
            top_strengths=strengths,
        )

    @staticmethod
    def _concerns_and_strengths(factors: GoNoGoFactors) -> tuple[list[str], list[str]]:
        as_dict = factors.model_dump()
        labels = {
            "win_probability": "احتمالية الفوز",
            "expected_margin": "الهامش المتوقع",
            "strategic_value": "القيمة الاستراتيجية",
            "capacity_match": "تطابق الطاقة الإنتاجية",
            "effort_required": "حجم الجهد المطلوب",
            "cash_flow_impact": "تأثير التدفق النقدي",
        }
        ranked = sorted(as_dict.items(), key=lambda kv: kv[1])
        concerns = [f"{labels[k]} منخفض ({v:.0%})" for k, v in ranked[:3] if v < 0.5]
        strengths = [f"{labels[k]} مرتفع ({v:.0%})" for k, v in ranked[-3:][::-1] if v > 0.7]
        return concerns, strengths

    @staticmethod
    def _reasoning(recommendation: str, factors: GoNoGoFactors, input_: GoNoGoInput) -> str:
        if recommendation == "GO":
            return (
                f"التقييم الشامل {factors.win_probability:.0%} فوز و"
                f"{factors.expected_margin:.0%} هامش يدعم الدخول. "
                f"عدد المنافسين المتوقع {input_.expected_competitors}."
            )
        if recommendation == "REVIEW":
            return (
                "التقييم متذبذب — يُنصح بمراجعة العوامل الضعيفة قبل اتخاذ القرار النهائي."
            )
        return (
            "العوامل الأساسية أقل من العتبة المقبولة. الدخول في هذه المنافسة "
            "يُهدر موارد بدون عائد متوقع كافٍ."
        )
