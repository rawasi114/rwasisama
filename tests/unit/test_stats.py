"""Stats utility tests."""

import pytest

from api.utils.stats import (
    clamp,
    weighted_mean,
    weighted_median,
    weighted_percentile,
    weighted_std,
)


def test_weighted_mean_basic():
    assert weighted_mean([1.0, 2.0, 3.0], [1.0, 1.0, 1.0]) == 2.0


def test_weighted_mean_unequal_weights():
    assert weighted_mean([1.0, 5.0], [3.0, 1.0]) == 2.0


def test_weighted_median_basic():
    assert weighted_median([1.0, 2.0, 3.0, 4.0, 5.0], [1.0] * 5) == 3.0


def test_weighted_percentile():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    weights = [1.0] * 5
    assert weighted_percentile(values, weights, 25) <= 20.0
    assert weighted_percentile(values, weights, 75) >= 40.0


def test_weighted_std_basic():
    assert weighted_std([5.0, 5.0, 5.0], [1.0, 1.0, 1.0]) == 0.0


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10


def test_empty_values():
    assert weighted_mean([], []) == 0.0
    assert weighted_median([], []) == 0.0


def test_weighted_percentile_invalid_range():
    with pytest.raises(ValueError):
        weighted_percentile([1.0], [1.0], -1)
    with pytest.raises(ValueError):
        weighted_percentile([1.0], [1.0], 101)
