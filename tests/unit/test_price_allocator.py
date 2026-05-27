"""Reverse price allocator tests — these protect the invariant that
sum(unit_price * quantity) equals the award value exactly."""

from uuid import uuid4

import pytest

from api.core.errors import AllocationError
from api.services.price_allocator import (
    AllocationInput,
    PriceAllocator,
)


def _make_items(refs):
    """Helper: build a list of items with quantity=1.0 and the given refs."""
    return [
        AllocationInput(
            boq_item_id=uuid4(),
            master_item_id=uuid4(),
            quantity=1.0,
            reference_price=r,
            reference_confidence=0.8,
        )
        for r in refs
    ]


class TestAllocationInvariant:
    def test_sum_equals_award_value_exact_match(self):
        items = _make_items([100.0, 200.0, 300.0])
        award = 600.0
        allocator = PriceAllocator()
        results = allocator.allocate(items, award)

        total = sum(r.total_price for r in results)
        assert abs(total - award) < 0.01

    def test_sum_equals_award_value_with_discount(self):
        items = _make_items([100.0, 200.0, 300.0])
        award = 540.0  # 10% discount
        results = PriceAllocator().allocate(items, award)
        total = sum(r.total_price for r in results)
        assert abs(total - award) < 0.01

    def test_sum_equals_award_value_with_uplift(self):
        items = _make_items([100.0, 200.0, 300.0])
        award = 720.0  # 20% uplift
        results = PriceAllocator().allocate(items, award)
        total = sum(r.total_price for r in results)
        assert abs(total - award) < 0.01


class TestAllocationLogic:
    def test_specialty_resists_discount_more_than_commodity(self):
        common = AllocationInput(
            boq_item_id=uuid4(),
            master_item_id=uuid4(),
            quantity=10.0,
            reference_price=100.0,
            reference_confidence=0.9,
            category_hint="commodity",
        )
        specialty = AllocationInput(
            boq_item_id=uuid4(),
            master_item_id=uuid4(),
            quantity=10.0,
            reference_price=100.0,
            reference_confidence=0.9,
            category_hint="specialty",
        )
        market = 2 * 100 * 10
        award = market * 0.85
        results = PriceAllocator().allocate([common, specialty], award)
        commodity_disc = (100.0 - results[0].unit_price) / 100.0
        specialty_disc = (100.0 - results[1].unit_price) / 100.0
        assert commodity_disc > specialty_disc

    def test_validates_positive_award_value(self):
        with pytest.raises(AllocationError):
            PriceAllocator().allocate(_make_items([100]), 0)
        with pytest.raises(AllocationError):
            PriceAllocator().allocate(_make_items([100]), -100)

    def test_validates_non_empty_items(self):
        with pytest.raises(AllocationError):
            PriceAllocator().allocate([], 1000.0)

    def test_validates_positive_quantities(self):
        item = AllocationInput(
            boq_item_id=uuid4(),
            master_item_id=uuid4(),
            quantity=0,
            reference_price=100.0,
        )
        with pytest.raises(AllocationError):
            PriceAllocator().allocate([item], 1000.0)


class TestAllocationFallback:
    def test_uniform_fallback_when_no_references(self):
        items = [
            AllocationInput(
                boq_item_id=uuid4(),
                master_item_id=None,
                quantity=10.0,
                reference_price=None,
            ),
            AllocationInput(
                boq_item_id=uuid4(),
                master_item_id=None,
                quantity=5.0,
                reference_price=None,
            ),
        ]
        results = PriceAllocator().allocate(items, 150.0)
        # uniform fallback gives same unit_price per quantity
        # since both have None refs, the fallback price is 1.0
        # then it's normalized to total 150
        total = sum(r.total_price for r in results)
        assert abs(total - 150.0) < 0.01

    def test_confidence_decreases_with_extreme_discount(self):
        items = _make_items([100.0, 100.0, 100.0])
        normal = PriceAllocator().allocate(items, 290.0)  # 3% discount
        extreme = PriceAllocator().allocate(items, 100.0)  # 67% discount
        assert max(r.confidence for r in extreme) < max(
            r.confidence for r in normal
        )
