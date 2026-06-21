"""Unit tests for the NudgeEngine service class.

This module tests that carbon outputs are converted into appropriate,
relatable everyday comparisons (phone charges, tree days, household days).
"""

from app.services.nudge_engine import NudgeEngine


def test_nudge_zero_emissions_walk() -> None:
    """Verifies walk zero-emission nudge text contains walking/biking message."""
    nudge = NudgeEngine.generate_nudge("transport", "walk", 0.0)
    assert "Zero emissions" in nudge
    assert "walking or biking" in nudge


def test_nudge_zero_emissions_other() -> None:
    """Verifies general zero-emission nudge text."""
    nudge = NudgeEngine.generate_nudge("food", "veg", 0.0)
    assert "no carbon impact" in nudge


def test_nudge_low_emissions() -> None:
    """Verifies low-emission actions compare to smartphone charges."""
    # 0.1 kg CO2. Phone charge is 0.0083 kg. 0.1 / 0.0083 = 12 charges
    nudge = NudgeEngine.generate_nudge("energy", "appliance", 0.1)
    assert "charging your smartphone 12 times" in nudge


def test_nudge_low_emissions_single_charge() -> None:
    """Verifies low-emission actions compare to single smartphone charge."""
    # 0.008 kg CO2. Phone charge is 0.0083 kg. 0.008 / 0.0083 = 1 charge
    nudge = NudgeEngine.generate_nudge("energy", "appliance", 0.008)
    assert "charging a smartphone once" in nudge


def test_nudge_medium_emissions_tree_days() -> None:
    """Verifies medium-emission actions compare to tree days."""
    # 0.6 kg CO2. Tree absorbs 0.06 kg/day. 0.6 / 0.06 = 10 tree days.
    nudge = NudgeEngine.generate_nudge("food", "mixed", 0.6)
    assert "tree absorbs in 10 days" in nudge


def test_nudge_medium_emissions_phone_months() -> None:
    """Verifies higher medium-emission actions compare to phone charging over months."""
    # 5.0 kg CO2. 5.0 / 0.0083 = 602 charges. 602 / 30.4 = 20 months.
    nudge = NudgeEngine.generate_nudge("transport", "car", 5.0)
    assert "smartphone every day for 20 months" in nudge


def test_nudge_high_emissions_house_days() -> None:
    """Verifies high-emission actions compare to household electricity days."""
    # 25.0 kg CO2. Household day is 10.0 kg. 25.0 / 10.0 = 2.5 household days.
    nudge = NudgeEngine.generate_nudge("transport", "flight", 25.0)
    assert "2.5 days of average household electricity" in nudge


def test_nudge_high_emissions_house_single_day() -> None:
    """Verifies high-emission action exactly matching a single household day."""
    # 10.0 kg CO2. 10.0 / 10.0 = 1.0 day.
    nudge = NudgeEngine.generate_nudge("transport", "flight", 10.0)
    assert "full day of average household electricity" in nudge


# ── Exact threshold boundaries ────────────────────────────────────────────────

def test_nudge_boundary_just_below_0_5kg() -> None:
    """co2 = 0.499 → still low-emission (smartphone charges) branch."""
    nudge = NudgeEngine.generate_nudge("transport", "bus", 0.499)
    # 0.499 / 0.0083 = ~60 charges
    assert "charging your smartphone" in nudge
    assert "times" in nudge


def test_nudge_boundary_exactly_0_5kg() -> None:
    """co2 = 0.5 → enters medium-emission (tree days) branch."""
    nudge = NudgeEngine.generate_nudge("transport", "bus", 0.5)
    # 0.5 / 0.06 = ~8 tree days, which is < 30 → tree branch
    assert "tree absorbs" in nudge


def test_nudge_boundary_just_below_8_0kg() -> None:
    """co2 = 7.99 → still medium-emission branch."""
    nudge = NudgeEngine.generate_nudge("transport", "car", 7.99)
    # 7.99 / 0.06 = ~133 tree days >= 30 → phone months branch
    assert "smartphone every day for" in nudge


def test_nudge_boundary_exactly_8_0kg() -> None:
    """co2 = 8.0 → enters high-emission (household days) branch."""
    nudge = NudgeEngine.generate_nudge("transport", "car", 8.0)
    # 8.0 / 10.0 = 0.8 < 1.0 → tree years sub-branch
    assert "tree absorbs" in nudge or "years" in nudge


def test_nudge_boundary_just_above_8_0kg() -> None:
    """co2 = 8.01 → high-emission branch, house_days < 1 → tree years."""
    nudge = NudgeEngine.generate_nudge("energy", "ac", 8.01)
    assert "tree absorbs" in nudge or "years" in nudge


def test_nudge_zero_emissions_bike() -> None:
    """bike type should also trigger the zero-emission walk/bike message."""
    nudge = NudgeEngine.generate_nudge("transport", "bike", 0.0)
    assert "Zero emissions" in nudge


def test_nudge_medium_phone_weeks_branch() -> None:
    """co2=1.0 → tree_days=17 < 30, so tree-days branch fires."""
    # 1.0 / 0.06 = 16.67 → rounds to 17 tree days
    nudge = NudgeEngine.generate_nudge("food", "meat-heavy", 1.0)
    assert "tree absorbs in 17 days" in nudge


def test_nudge_medium_phone_months_at_5kg() -> None:
    """5.0kg → tree_days=83 >= 30, months=20 → months branch."""
    nudge = NudgeEngine.generate_nudge("transport", "car", 5.0)
    assert "smartphone every day for 20 months" in nudge
