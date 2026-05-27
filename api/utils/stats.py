"""Lightweight weighted-statistics helpers used across the analytics engines."""

from __future__ import annotations

import math
from collections.abc import Sequence


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    if not values:
        return 0.0
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length")
    total = sum(weights)
    if total <= 0:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights, strict=True)) / total


def weighted_percentile(
    values: Sequence[float], weights: Sequence[float], percentile: float
) -> float:
    """Return the ``percentile`` (0..100) of ``values`` weighted by ``weights``."""
    if not values:
        return 0.0
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")
    pairs = sorted(zip(values, weights, strict=True), key=lambda x: x[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        idx = max(0, min(len(pairs) - 1, int(len(pairs) * percentile / 100)))
        return pairs[idx][0]
    target = total * percentile / 100
    cumulative = 0.0
    for v, w in pairs:
        cumulative += w
        if cumulative >= target:
            return v
    return pairs[-1][0]


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    return weighted_percentile(values, weights, 50)


def weighted_std(values: Sequence[float], weights: Sequence[float]) -> float:
    if not values:
        return 0.0
    mu = weighted_mean(values, weights)
    total = sum(weights)
    if total <= 0:
        n = len(values)
        return math.sqrt(sum((v - mu) ** 2 for v in values) / n)
    variance = sum(w * (v - mu) ** 2 for v, w in zip(values, weights, strict=True)) / total
    return math.sqrt(max(0.0, variance))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
