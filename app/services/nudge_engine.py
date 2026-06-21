"""Nudge engine for generating relatable carbon comparisons.

This module converts CO2 emissions (in kg) into relatable everyday
comparisons such as smartphone charges, tree-absorption days, and
household electricity usage.
"""


class NudgeEngine:
    """Service to generate instant relatable comparison nudges from CO2 amounts.

    Equivalences used:
    - 1 Smartphone charge  = 0.0083 kg CO2 (8.3 g)
    - 1 Tree absorption day = 0.06 kg CO2 (60 g, based on 22 kg/year)
    - 1 Household electricity day = 10.0 kg CO2
    """

    PHONE_CHARGE_CO2: float = 0.0083
    TREE_DAY_CO2: float = 0.06
    HOUSEHOLD_DAY_CO2: float = 10.0

    @classmethod
    def generate_nudge(cls, category: str, action_type: str, co2_kg: float) -> str:
        """Generates a comparison nudge based on the category and carbon quantity.

        Args:
            category: Action category (transport, food, energy). Reserved for
                future per-category nudge specialisation.
            action_type: Specific action type (e.g. car, veg, ac).
            co2_kg: Emissions in kg.

        Returns:
            A human-relatable comparison nudge string.
        """
        _ = category  # reserved for future per-category specialisation
        type_lower = action_type.lower()

        if co2_kg <= 0.0:
            return cls._zero_emission_nudge(type_lower)
        if co2_kg < 0.5:
            return cls._low_emission_nudge(type_lower, co2_kg)
        if co2_kg < 8.0:
            return cls._medium_emission_nudge(type_lower, co2_kg)
        return cls._high_emission_nudge(type_lower, co2_kg)

    # ── Private helpers ────────────────────────────────────────────────────────

    @classmethod
    def _zero_emission_nudge(cls, type_lower: str) -> str:
        """Returns a nudge for zero-emission actions.

        Args:
            type_lower: Lowercased action type.

        Returns:
            A nudge string celebrating zero emissions.
        """
        if type_lower in ("walk", "bike"):
            return (
                "Zero emissions! By walking or biking instead of driving, "
                "you kept the air clean and generated no greenhouse gases."
            )
        return "Great choice! This action has no carbon impact."

    @classmethod
    def _low_emission_nudge(cls, type_lower: str, co2_kg: float) -> str:
        """Returns a nudge comparing low emissions to smartphone charges.

        Args:
            type_lower: Lowercased action type.
            co2_kg: Emissions in kg (must be in range (0, 0.5)).

        Returns:
            A nudge string referencing smartphone charge counts.
        """
        charges = round(co2_kg / cls.PHONE_CHARGE_CO2)
        if charges <= 1:
            return (
                f"That {type_lower} choice = {co2_kg}kg CO2 = charging a smartphone once."
            )
        return (
            f"That {type_lower} choice = {co2_kg}kg CO2 = "
            f"charging your smartphone {charges} times."
        )

    @classmethod
    def _medium_emission_nudge(cls, type_lower: str, co2_kg: float) -> str:
        """Returns a nudge for medium emissions (tree days or phone-charge duration).

        Args:
            type_lower: Lowercased action type.
            co2_kg: Emissions in kg (must be in range [0.5, 8.0)).

        Returns:
            A nudge string referencing tree absorption days or charging duration.
        """
        tree_days = round(co2_kg / cls.TREE_DAY_CO2)
        if tree_days < 30:
            return (
                f"That {type_lower} activity = {co2_kg}kg CO2 = the amount of CO2 "
                f"a mature tree absorbs in {tree_days} days."
            )
        return cls._phone_charge_duration_nudge(type_lower, co2_kg)

    @classmethod
    def _phone_charge_duration_nudge(cls, type_lower: str, co2_kg: float) -> str:
        """Returns a nudge phrased as weeks or months of daily phone charging.

        Args:
            type_lower: Lowercased action type.
            co2_kg: Emissions in kg.

        Returns:
            A nudge string referencing charging duration in weeks or months.
        """
        total_charges = co2_kg / cls.PHONE_CHARGE_CO2
        months = round(total_charges / 30.4)
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

    @classmethod
    def _high_emission_nudge(cls, type_lower: str, co2_kg: float) -> str:
        """Returns a nudge comparing high emissions to household electricity days.

        Args:
            type_lower: Lowercased action type.
            co2_kg: Emissions in kg (must be >= 8.0).

        Returns:
            A nudge string referencing household electricity days or tree years.
        """
        house_days = round(co2_kg / cls.HOUSEHOLD_DAY_CO2, 1)
        if house_days < 1.0:
            tree_years = round(co2_kg / (cls.TREE_DAY_CO2 * 365), 1)
            return (
                f"That {type_lower} trip = {co2_kg}kg CO2 = the amount of carbon "
                f"a mature tree absorbs over {tree_years} years."
            )
        if house_days == 1.0:
            return (
                f"That {type_lower} trip = {co2_kg}kg CO2 = a full day of average "
                f"household electricity usage."
            )
        return (
            f"That {type_lower} trip = {co2_kg}kg CO2 = {house_days} days of "
            f"average household electricity usage."
        )
