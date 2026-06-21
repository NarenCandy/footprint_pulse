"""User model for the Footprint Pulse application.

This module defines the User dataclass for representing an individual user's
profile and target daily carbon budgets.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class User:
    """Dataclass representing a user profile.

    Attributes:
        id: Unique identifier for the user.
        name: Name of the user.
        daily_target_co2: Target daily carbon footprint in kilograms.
    """

    id: str
    name: str
    daily_target_co2: float

    def to_dict(self) -> Dict[str, Any]:
        """Converts the User instance to a dictionary.

        Returns:
            A dictionary representation of the User.
        """
        return {
            "id": self.id,
            "name": self.name,
            "daily_target_co2": self.daily_target_co2,
        }
