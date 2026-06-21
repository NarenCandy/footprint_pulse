"""Carbon calculation service for the Footprint Pulse application.

This module provides utility functions to calculate the carbon emissions (CO2 in kg)
for various categories of actions (transport, food, energy) based on EPA and IPCC
approximate averages.
"""

from typing import Dict


class CarbonCalculator:
    """Service to calculate carbon emissions for various activities.

    Calculations use a pre-defined lookup table of emission factors (kg CO2 per unit)
    which is cached in memory at startup.
    """

    # Static carbon factor lookup table cached in memory.
    # Units:
    # - transport: kg CO2 per unit (km or hour of flight)
    # - food: kg CO2 per meal
    # - energy: kg CO2 per hour
    EMISSION_FACTORS: Dict[str, Dict[str, float]] = {
        "transport": {
            "walk": 0.0,      # Walk/bike has zero emissions
            "bike": 0.0,
            "bus": 0.089,     # Average bus emission per passenger-km (approx 89g)
            "metro": 0.035,    # Average metro/train per passenger-km (approx 35g)
            "car": 0.171,     # Average passenger car emission per km (approx 171g)
            "flight": 150.0,   # Average passenger flight emission per hour (approx 150kg)
        },
        "food": {
            "veg": 0.7,        # Vegan/Vegetarian meal (approx 0.7kg)
            "mixed": 1.5,      # Balanced/mixed diet meal (approx 1.5kg)
            "meat-heavy": 3.0, # Meat-heavy meal (approx 3.0kg)
        },
        "energy": {
            "ac": 0.75,        # 1.5kW AC running for 1 hour at 0.5 kg CO2/kWh
            "appliance": 0.25, # Typical household appliances (approx 500W total, 0.25kg/hr)
        },
    }

    @classmethod
    def calculate_co2(cls, category: str, action_type: str, amount: float) -> float:
        """Calculates carbon footprint for a given action.

        Args:
            category: Action category (transport, food, energy).
            action_type: Specific action type (e.g. car, veg, ac).
            amount: Quantity/scale of action (e.g. km, hours, meals).

        Returns:
            CO2 emissions in kilograms.

        Raises:
            ValueError: If the category or action type is invalid.
        """
        cat_lower = category.lower()
        type_lower = action_type.lower()

        if cat_lower not in cls.EMISSION_FACTORS:
            raise ValueError(f"Invalid category: '{category}'")

        factors = cls.EMISSION_FACTORS[cat_lower]
        if type_lower not in factors:
            raise ValueError(
                f"Invalid action type: '{action_type}' for category: '{category}'"
            )

        factor = factors[type_lower]
        # Return calculated CO2 rounded to 3 decimal places
        return round(factor * amount, 3)
