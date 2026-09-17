"""Tier-weight tests."""
from patchcourt.config import TIER_WEIGHTS


def test_tier_weights_exact():
    assert TIER_WEIGHTS == {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.4, 5: 0.1}


def test_tier_monotonic_decreasing():
    assert TIER_WEIGHTS[1] > TIER_WEIGHTS[2] > TIER_WEIGHTS[3] > TIER_WEIGHTS[4] > TIER_WEIGHTS[5]


def test_t5_weight_is_lowest():
    assert TIER_WEIGHTS[5] < TIER_WEIGHTS[4] and TIER_WEIGHTS[5] < 0.2