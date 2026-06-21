"""Nudge engine for generating relatable carbon comparisons.

This module converts carbon dioxide emissions (in kg) into relatable everyday comparisons,
such as smartphone charges, tree-absorption days, and household electricity usage.
"""

import math


class NudgeEngine:
    """Service to generate instant relatable comparison nudges from CO2 amounts.

    Equivalences used:
    - 1 Smartphone charge = 0.0083 kg CO2 (8.3g)
    - 1 Tree absorption day = 0.06 kg CO2 (60g, based on 22kg/year)
    - 1 Household electricity day = 10.0 kg CO2
    """

    PHONE_CHARGE_CO2: float = 0.0083
    TREE_DAY_CO2: float = 0.06
    HOUSEHOLD_DAY_CO2: float = 10.0

    @classmethod
    def generate_nudge(cls, category: str, action_type: str, co2_kg: float) -> str:
        """Generates a comparison nudge based on the category and carbon quantity.

        Args:
            category: Action category (transport, food, energy).
            action_type: Specific action type (e.g. car, veg, ac).
            co2_kg: Emissions in kg.

        Returns:
            A human-relatable comparison nudge string.
        """
        cat_lower = category.lower()
        type_lower = action_type.lower()

        # Handle zero-emissions path (e.g. walk/bike)
        if co2_kg <= 0.0:
            if type_lower in ["walk", "bike"]:
                return (
                    "Zero emissions! By walking or biking instead of driving, "
                    "you kept the air clean and generated no greenhouse gases."
                )
            return "Great choice! This action has no carbon impact."

        # Dynamically select equivalence based on size of carbon footprint
        if co2_kg < 0.5:
            # Low emission -> compare to smartphone charges
            charges = round(co2_kg / cls.PHONE_CHARGE_CO2)
            if charges <= 1:
                return f"That {type_lower} choice = {co2_kg}kg CO2 = charging a smartphone once."
            return f"That {type_lower} choice = {co2_kg}kg CO2 = charging your smartphone {charges} times."

        if co2_kg < 8.0:
            # Medium emission -> compare to tree days or smartphone charge duration
            tree_days = round(co2_kg / cls.TREE_DAY_CO2)
            if tree_days < 30:
                return (
                    f"That {type_lower} activity = {co2_kg}kg CO2 = the amount of CO2 "
                    f"a mature tree absorbs in {tree_days} days."
                )
            
            # Format as weeks/months of smartphone charging
            total_charges = co2_kg / cls.PHONE_CHARGE_CO2
            months = round(total_charges / 30.4)  # Average days in a month
            if months <= 1:
                weeks = round(total_charges / 7.0)
                if weeks <= 1:
                    return (
                        f"That {type_lower} activity = {co2_kg}kg CO2 = charging "
                        f"your smartphone every day for a week."
                    )
                return (
                    f"That {type_lower} activity = {co2_kg}kg CO2 = charging "
                    f"your smartphone every day for {weeks} weeks."
                )
            return (
                f"That {type_lower} activity = {co2_kg}kg CO2 = charging "
                f"your smartphone every day for {months} months."
            )

        # High emission -> compare to household electricity days or tree absorption years
        house_days = round(co2_kg / cls.HOUSEHOLD_DAY_CO2, 1)
        if house_days < 1.0:
            tree_years = round(co2_kg / (cls.TREE_DAY_CO2 * 365), 1)
            return (
                f"That {type_lower} trip = {co2_kg}kg CO2 = the amount of carbon "
                f"a mature tree absorbs over {tree_years} years."
            )
        
        # Format house days
        if house_days == 1.0:
            return (
                f"That {type_lower} trip = {co2_kg}kg CO2 = a full day of average "
                f"household electricity usage."
            )
        return (
            f"That {type_lower} trip = {co2_kg}kg CO2 = {house_days} days of "
            f"average household electricity usage."
        )
