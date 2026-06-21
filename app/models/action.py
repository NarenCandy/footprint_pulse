"""Action model and repository for the Footprint Pulse application.

This module defines the Action dataclass representing a logged carbon action
and the ActionRepository implementing the repository pattern for thread-safe
in-memory storage of logged actions.
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Action:
    """Dataclass representing a logged carbon action.

    Attributes:
        id: Unique identifier for the action.
        category: Category of the action (transport, food, energy).
        type: Specific type of the action (e.g. car, bus, veg, AC).
        amount: Numerical value representing the scale/quantity of the action.
        unit: Unit of measurement (e.g. km, meals, hours).
        co2_kg: Calculated CO2 emissions in kilograms.
        nudge: Instantly generated comparison nudge text.
        timestamp: Time the action was logged.
    """

    id: str
    category: str
    type: str
    amount: float
    unit: str
    co2_kg: float
    nudge: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Converts the Action instance to a serialisable dictionary.

        Returns:
            A dictionary representation of the Action with timestamp as ISO
            format string.
        """
        return {
            "id": self.id,
            "category": self.category,
            "type": self.type,
            "amount": self.amount,
            "unit": self.unit,
            "co2_kg": self.co2_kg,
            "nudge": self.nudge,
            "timestamp": self.timestamp.isoformat(),
        }


class ActionRepository:
    """Thread-safe in-memory repository for storing Actions."""

    def __init__(self) -> None:
        """Initialises the repository with an empty list and a threading lock."""
        self._actions: list[Action] = []
        self._lock: threading.Lock = threading.Lock()

    def add(self, action: Action) -> Action:
        """Adds a new Action to the repository.

        Args:
            action: The Action instance to store.

        Returns:
            The added Action.
        """
        with self._lock:
            self._actions.append(action)
            return action

    def get_all(self) -> list[Action]:
        """Retrieves all logged actions, sorted by timestamp descending.

        Returns:
            A list of all stored Actions ordered newest-first.
        """
        with self._lock:
            return sorted(self._actions, key=lambda a: a.timestamp, reverse=True)

    def clear(self) -> None:
        """Clears all stored actions. Useful for testing."""
        with self._lock:
            self._actions.clear()

    def get_total_co2(self) -> float:
        """Calculates the total CO2 emissions across all logged actions.

        Returns:
            Total CO2 in kilograms.
        """
        with self._lock:
            return sum(action.co2_kg for action in self._actions)

    def get_category_totals(self) -> dict[str, float]:
        """Calculates total CO2 emissions aggregated by category.

        Returns:
            A dictionary mapping category name to total CO2 emissions in kg.
            Always contains keys 'transport', 'food', and 'energy'; unknown
            categories are added dynamically.
        """
        with self._lock:
            totals: dict[str, float] = {
                "transport": 0.0,
                "food": 0.0,
                "energy": 0.0,
            }
            for action in self._actions:
                if action.category in totals:
                    totals[action.category] += action.co2_kg
                else:
                    totals[action.category] = action.co2_kg
            return totals
