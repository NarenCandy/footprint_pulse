"""Unit tests for the CarbonCalculator service class.

This module tests emission calculations and error cases for transport,
food, and energy carbon calculations.
"""

import pytest
from app.services.carbon_calculator import CarbonCalculator


def test_calculate_co2_transport_walk() -> None:
    """Verifies that walking results in 0.0 carbon emissions."""
    co2 = CarbonCalculator.calculate_co2("transport", "walk", 10.0)
    assert co2 == 0.0


def test_calculate_co2_transport_bike() -> None:
    """Verifies that biking results in 0.0 carbon emissions."""
    co2 = CarbonCalculator.calculate_co2("transport", "bike", 5.0)
    assert co2 == 0.0


def test_calculate_co2_transport_car() -> None:
    """Verifies correct calculation for car travel based on standard factor."""
    # Factor: 0.171 kg/km. 10km = 1.71 kg
    co2 = CarbonCalculator.calculate_co2("transport", "car", 10.0)
    assert co2 == 1.71


def test_calculate_co2_transport_bus() -> None:
    """Verifies correct calculation for bus travel based on standard factor."""
    # Factor: 0.089 kg/km. 20km = 1.78 kg
    co2 = CarbonCalculator.calculate_co2("transport", "bus", 20.0)
    assert co2 == 1.78


def test_calculate_co2_transport_metro() -> None:
    """Verifies correct calculation for metro travel based on standard factor."""
    # Factor: 0.035 kg/km. 10km = 0.35 kg
    co2 = CarbonCalculator.calculate_co2("transport", "metro", 10.0)
    assert co2 == 0.35


def test_calculate_co2_transport_flight() -> None:
    """Verifies correct calculation for flights based on hourly standard factor."""
    # Factor: 150 kg/hour. 2 hours = 300.0 kg
    co2 = CarbonCalculator.calculate_co2("transport", "flight", 2.0)
    assert co2 == 300.0


def test_calculate_co2_food_veg() -> None:
    """Verifies correct calculation for vegetarian food meal."""
    # Factor: 0.7 kg/meal. 3 meals = 2.1 kg
    co2 = CarbonCalculator.calculate_co2("food", "veg", 3.0)
    assert co2 == 2.1


def test_calculate_co2_food_mixed() -> None:
    """Verifies correct calculation for mixed food meal."""
    # Factor: 1.5 kg/meal. 2 meals = 3.0 kg
    co2 = CarbonCalculator.calculate_co2("food", "mixed", 2.0)
    assert co2 == 3.0


def test_calculate_co2_food_meat_heavy() -> None:
    """Verifies correct calculation for meat-heavy meal."""
    # Factor: 3.0 kg/meal. 1 meal = 3.0 kg
    co2 = CarbonCalculator.calculate_co2("food", "meat-heavy", 1.0)
    assert co2 == 3.0


def test_calculate_co2_energy_ac() -> None:
    """Verifies correct calculation for AC energy consumption."""
    # Factor: 0.75 kg/hour. 4 hours = 3.0 kg
    co2 = CarbonCalculator.calculate_co2("energy", "ac", 4.0)
    assert co2 == 3.0


def test_calculate_co2_energy_appliance() -> None:
    """Verifies correct calculation for household appliance energy."""
    # Factor: 0.25 kg/hour. 8 hours = 2.0 kg
    co2 = CarbonCalculator.calculate_co2("energy", "appliance", 8.0)
    assert co2 == 2.0


def test_calculate_co2_invalid_category() -> None:
    """Verifies that an invalid category raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid category"):
        CarbonCalculator.calculate_co2("manufacturing", "car", 10.0)


def test_calculate_co2_invalid_type() -> None:
    """Verifies that an invalid type raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid action type"):
        CarbonCalculator.calculate_co2("transport", "rocket", 10.0)


def test_calculate_co2_case_insensitivity() -> None:
    """Verifies that calculation input is case-insensitive."""
    co2 = CarbonCalculator.calculate_co2("TraNsPort", "CaR", 10.0)
    assert co2 == 1.71
