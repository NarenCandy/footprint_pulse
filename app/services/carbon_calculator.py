"""Carbon calculation service for the Footprint Pulse application.

This module provides utility functions to calculate the carbon emissions
(CO2 in kg) for various categories of actions (transport, food, energy)
based on EPA and IPCC approximate averages.
"""


class CarbonCalculator:
    """Service to calculate carbon emissions for various activities.

    Calculations use a pre-defined lookup table of emission factors
    (kg CO2 per unit) cached in memory at startup.
    """

    # Static carbon factor lookup table cached in memory.
    # Units:
    #   transport : kg CO2 per km (or per hour for flight)
    #   food      : kg CO2 per meal
    #   energy    : kg CO2 per hour
    EMISSION_FACTORS: dict[str, dict[str, float]] = {
        "transport": {
            "walk": 0.0,       # Walk/bike — zero emissions
            "bike": 0.0,
            "bus": 0.089,      # Average bus per passenger-km (~89 g)
            "metro": 0.035,    # Average metro/train per passenger-km (~35 g)
            "car": 0.171,      # Average passenger car per km (~171 g)
            "flight": 150.0,   # Average passenger flight per hour (~150 kg)
        },
        "food": {
            "veg": 0.7,          # Vegan/Vegetarian meal (~0.7 kg)
            "mixed": 1.5,        # Balanced/mixed diet meal (~1.5 kg)
            "meat-heavy": 3.0,   # Meat-heavy meal (~3.0 kg)
        },
        "energy": {
            "ac": 0.75,        # 1.5 kW AC for 1 hr at 0.5 kg CO2/kWh
            "appliance": 0.25, # Typical household appliances (~500 W, 0.25 kg/hr)
        },
    }

    @classmethod
    def calculate_co2(
        cls, category: str, action_type: str, amount: float
    ) -> float:
        """Calculates the carbon footprint for a given action.

        Args:
            category: Action category (transport, food, energy).
            action_type: Specific action type (e.g. car, veg, ac).
            amount: Quantity/scale of the action (e.g. km, hours, meals).

        Returns:
            CO2 emissions in kilograms rounded to 3 decimal places.

        Raises:
            ValueError: If the category or action type is not recognised.
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

        return round(factors[type_lower] * amount, 3)
