"""Gemini service module for generating weekly personalised carbon insights.

This service uses the Google Gemini API to analyse logged actions and suggest
tailored reduction levers. It includes a 5-second timeout and falls back to
a deterministic rule-based recommendation generator if the API is offline,
misconfigured, or times out.
"""

import concurrent.futures
import logging
import os
from dataclasses import dataclass

import google.generativeai as genai

from app.models.action import Action

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-1.5-flash"
_GEMINI_TIMEOUT = 5.0


@dataclass
class _ActionTally:
    """Accumulator for per-category CO2 and action counts.

    Attributes:
        transport_co2: Total transport CO2 in kg.
        food_co2: Total food CO2 in kg.
        energy_co2: Total energy CO2 in kg.
        car_count: Number of car trips logged.
        flight_count: Number of flight hours logged.
        meat_count: Number of meat-heavy meals logged.
        ac_hours: Total AC hours logged.
    """

    transport_co2: float = 0.0
    food_co2: float = 0.0
    energy_co2: float = 0.0
    car_count: int = 0
    flight_count: int = 0
    meat_count: int = 0
    ac_hours: float = 0.0


class GeminiService:
    """Generates weekly carbon insights via Gemini AI with a rule-based fallback."""

    def __init__(self) -> None:
        """Initialises the Gemini service, configuring the SDK when an API key is present."""
        self.api_key: str | None = os.environ.get("GEMINI_API_KEY")
        self._fallback_active: bool = False
        self._executor: concurrent.futures.ThreadPoolExecutor = (
            concurrent.futures.ThreadPoolExecutor(max_workers=2)
        )

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self._fallback_active = False
                logger.info("Gemini service initialised successfully.")
            except Exception as exc:
                logger.error("Failed to configure Gemini SDK: %s", exc)
                self._fallback_active = True
        else:
            logger.warning("GEMINI_API_KEY not found. Rule-based fallback active.")
            self._fallback_active = True

    def is_degraded(self) -> bool:
        """Returns True when the rule-based fallback is active.

        Returns:
            True if Gemini is unavailable or unconfigured, False otherwise.
        """
        if not self.api_key:
            return True
        return self._fallback_active

    def generate_weekly_insight(
        self, actions: list[Action]
    ) -> tuple[str, bool]:
        """Generates a weekly personalised insight from logged actions.

        Attempts to call the Gemini API. Falls back to the rule-based engine
        on timeout, API error, or missing API key.

        Args:
            actions: The list of Actions logged by the user this week.

        Returns:
            A tuple of ``(insight_text, fallback_active)`` where
            ``fallback_active`` is True when the rule-based engine was used.
        """
        if not actions:
            return (
                "You haven't logged any actions yet! Start logging your daily "
                "transport, food, and energy actions using the buttons below to "
                "see your personalised weekly insights and carbon-reduction advice.",
                self.is_degraded(),
            )

        if self.is_degraded():
            return self._generate_rule_based_insight(actions), True

        prompt = self._build_prompt(actions)

        try:
            future = self._executor.submit(self._call_gemini_api, prompt)
            insight = future.result(timeout=_GEMINI_TIMEOUT)
            self._fallback_active = False
            return insight, False
        except concurrent.futures.TimeoutError:
            logger.warning(
                "Gemini API call timed out after %.1f seconds. Using fallback.",
                _GEMINI_TIMEOUT,
            )
            self._fallback_active = True
            return self._generate_rule_based_insight(actions), True
        except Exception as exc:
            logger.error("Error during Gemini API execution: %s. Using fallback.", exc)
            self._fallback_active = True
            return self._generate_rule_based_insight(actions), True

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_prompt(self, actions: list[Action]) -> str:
        """Builds the Gemini prompt string from the action summary.

        Args:
            actions: List of logged Actions.

        Returns:
            A prompt string ready to send to the Gemini API.
        """
        summary = self._summarize_actions(actions)
        return (
            "Analyze these carbon actions logged by a user this week and provide "
            "a short (2-3 sentences), highly actionable, encouraging, personalised "
            "weekly insight recommending their top reduction lever. Focus on the "
            "category with the highest emissions. Do not use markdown headers, "
            f"lists, bolding, or bullet points. Logged actions summary: {summary}."
        )

    def _call_gemini_api(self, prompt: str) -> str:
        """Invokes the Gemini API synchronously inside a thread worker.

        Args:
            prompt: The prompt string to send.

        Returns:
            The generated text content from Gemini.

        Raises:
            ValueError: If Gemini returns an empty response.
        """
        model = genai.GenerativeModel(_GEMINI_MODEL)
        response = model.generate_content(prompt)
        text: str = response.text.strip()
        if not text:
            raise ValueError("Empty response received from Gemini API.")
        return text

    def _summarize_actions(self, actions: list[Action]) -> str:
        """Creates a concise text summary of logged actions for the Gemini prompt.

        Args:
            actions: The list of Actions to summarise.

        Returns:
            A comma-separated summary string of action counts and CO2 totals.
        """
        counts: dict[str, int] = {}
        totals: dict[str, float] = {}
        for action in actions:
            key = f"{action.category} ({action.type})"
            counts[key] = counts.get(key, 0) + 1
            totals[key] = totals.get(key, 0.0) + action.co2_kg
        return ", ".join(
            f"{counts[k]}x {k} emitting total {totals[k]:.2f}kg CO2"
            for k in counts
        )

    @staticmethod
    def _tally_actions(actions: list[Action]) -> _ActionTally:
        """Aggregates action counts and CO2 totals by category into a tally.

        Args:
            actions: The list of Actions to aggregate.

        Returns:
            An ``_ActionTally`` instance with all counters populated.
        """
        tally = _ActionTally()
        for action in actions:
            if action.category == "transport":
                tally.transport_co2 += action.co2_kg
                if action.type == "car":
                    tally.car_count += 1
                elif action.type == "flight":
                    tally.flight_count += 1
            elif action.category == "food":
                tally.food_co2 += action.co2_kg
                if action.type == "meat-heavy":
                    tally.meat_count += 1
            elif action.category == "energy":
                tally.energy_co2 += action.co2_kg
                if action.type == "ac":
                    tally.ac_hours += action.amount
        return tally

    def _generate_rule_based_insight(self, actions: list[Action]) -> str:
        """Produces a deterministic weekly insight without calling any external API.

        Args:
            actions: List of Actions logged by the user.

        Returns:
            A customised advice string targeting the highest-emission category.
        """
        tally = self._tally_actions(actions)
        total_co2 = tally.transport_co2 + tally.food_co2 + tally.energy_co2

        if total_co2 == 0.0:
            return (
                "Amazing job! You have logged activities but generated zero carbon "
                "emissions this week. Keep walking, biking, and maintaining this "
                "sustainable lifestyle!"
            )

        max_cat = max(
            [
                ("transport", tally.transport_co2),
                ("food", tally.food_co2),
                ("energy", tally.energy_co2),
            ],
            key=lambda x: x[1],
        )[0]

        if max_cat == "transport":
            return self._transport_insight(tally)
        if max_cat == "food":
            return self._food_insight(tally)
        return self._energy_insight(tally)

    @staticmethod
    def _transport_insight(tally: _ActionTally) -> str:
        """Returns a transport-focused reduction insight.

        Args:
            tally: Populated ``_ActionTally`` instance.

        Returns:
            An advice string targeting transport emissions.
        """
        if tally.flight_count > 0:
            return (
                f"Your flights contributed {tally.transport_co2:.1f}kg CO2 this week. "
                "Since aviation has a massive carbon density, offsetting your flights "
                "or substituting short trips with high-speed rail is your top lever "
                "for reduction."
            )
        if tally.car_count > 0:
            return (
                f"You logged {tally.car_count} car trips this week, making transport "
                f"your highest emission source at {tally.transport_co2:.1f}kg CO2. "
                "Shifting just two of those trips to public transit, biking, or "
                "walking will reduce your footprint significantly."
            )
        return (
            f"Transport is your highest carbon contributor at "
            f"{tally.transport_co2:.1f}kg CO2. Try consolidating your errands or "
            "carpooling to lower your weekly commute emissions."
        )

    @staticmethod
    def _food_insight(tally: _ActionTally) -> str:
        """Returns a food-focused reduction insight.

        Args:
            tally: Populated ``_ActionTally`` instance.

        Returns:
            An advice string targeting food emissions.
        """
        if tally.meat_count > 0:
            return (
                f"You enjoyed meat-heavy meals {tally.meat_count} times this week, "
                f"putting your food footprint at {tally.food_co2:.1f}kg CO2. "
                "Shifting to vegetarian or mixed meals just a few days a week is a "
                "highly effective way to cut down your emissions."
            )
        return (
            f"Your dining choices contributed {tally.food_co2:.1f}kg CO2. "
            "Emphasising locally sourced, seasonal, plant-based ingredients is your "
            "best path to reduce food emissions."
        )

    @staticmethod
    def _energy_insight(tally: _ActionTally) -> str:
        """Returns an energy-focused reduction insight.

        Args:
            tally: Populated ``_ActionTally`` instance.

        Returns:
            An advice string targeting energy emissions.
        """
        if tally.ac_hours > 0.0:
            return (
                f"Your air conditioning ran for {tally.ac_hours:.1f} hours, driving "
                f"your energy emissions to {tally.energy_co2:.1f}kg CO2. Raising your "
                "AC thermostat by just 2 degrees or using a fan can decrease your "
                "cooling emissions by up to 15%."
            )
        return (
            f"Household energy consumption was your main emissions driver at "
            f"{tally.energy_co2:.1f}kg CO2. Consider unplugging standby electronics "
            "and switching to energy-efficient appliances to reduce baseline "
            "electricity usage."
        )
