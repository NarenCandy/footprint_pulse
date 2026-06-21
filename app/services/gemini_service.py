"""Gemini service module for generating weekly personalized carbon insights.

This service utilizes the Google Gemini API to analyze logged actions and suggest
tailored reduction levers. It includes a 5-second timeout and falls back to
a deterministic, rule-based recommendation generator if the API is offline,
misconfigured, or times out.
"""

import concurrent.futures
import logging
import os
from typing import List, Tuple
import google.generativeai as genai
from app.models.action import Action

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for generating weekly carbon footprint insights using Gemini or rule-based fallback."""

    def __init__(self) -> None:
        """Initializes the Gemini service, configuring the SDK if the API key is present."""
        self.api_key: str | None = os.environ.get("GEMINI_API_KEY")
        self._fallback_active: bool = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self._fallback_active = False
                logger.info("Gemini service initialized successfully.")
            except Exception as e:
                logger.error("Failed to configure Gemini SDK: %s", e)
                self._fallback_active = True
        else:
            logger.warning("GEMINI_API_KEY not found. Rule-based fallback active.")
            self._fallback_active = True

    def is_degraded(self) -> bool:
        """Checks if the service is currently degraded (operating on rule-based fallback).

        Returns:
            True if the rule-based fallback is active, False otherwise.
        """
        # If API key is not configured, we are degraded.
        if not self.api_key:
            return True
        return self._fallback_active

    def generate_weekly_insight(self, actions: List[Action]) -> Tuple[str, bool]:
        """Generates a weekly personalized insight based on logged actions.

        This method attempts to call the Gemini API. If the call fails, times out,
        or no API key is configured, it falls back to a rule-based algorithm.

        Args:
            actions: The list of Actions logged by the user.

        Returns:
            A tuple containing (insight_text, fallback_active).
        """
        if not actions:
            return (
                "You haven't logged any actions yet! Start logging your daily transport, "
                "food, and energy actions using the buttons below to see your personalized "
                "weekly insights and carbon-reduction advice.",
                self.is_degraded()
            )

        action_summary = self._summarize_actions(actions)

        # If key is missing or already marked degraded, use rule-based directly
        if self.is_degraded():
            return self._generate_rule_based_insight(actions), True

        # Run Gemini API call in a thread pool with a 5-second timeout
        prompt = (
            "Analyze these carbon actions logged by a user this week and provide a short "
            "(2-3 sentences), highly actionable, encouraging, personalized weekly insight "
            "recommending their top reduction lever. Focus on the category with the highest "
            "emissions. Do not use markdown headers, lists, bolding, or bullet points. "
            f"Logged actions summary: {action_summary}."
        )

        try:
            future = self._executor.submit(self._call_gemini_api, prompt)
            insight = future.result(timeout=5.0)
            # Successful API call, ensure fallback flag is False
            self._fallback_active = False
            return insight, False
        except concurrent.futures.TimeoutError:
            logger.warning("Gemini API call timed out after 5.0 seconds. Using fallback.")
            self._fallback_active = True
            return self._generate_rule_based_insight(actions), True
        except Exception as e:
            logger.error("Error during Gemini API execution: %s. Using fallback.", e)
            self._fallback_active = True
            return self._generate_rule_based_insight(actions), True

    def _call_gemini_api(self, prompt: str) -> str:
        """Helper to invoke the Gemini API. Runs inside a thread worker.

        Args:
            prompt: Prompt string.

        Returns:
            The generated text content.
        """
        # Using gemini-1.5-flash as it's the current recommended model for general tasks
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        if not text:
            raise ValueError("Empty response received from Gemini API.")
        return text

    def _summarize_actions(self, actions: List[Action]) -> str:
        """Creates a text summary of logged actions for the model prompt.

        Args:
            actions: The list of Actions.

        Returns:
            A string summary.
        """
        counts: dict[str, int] = {}
        totals: dict[str, float] = {}
        for a in actions:
            key = f"{a.category} ({a.type})"
            counts[key] = counts.get(key, 0) + 1
            totals[key] = totals.get(key, 0.0) + a.co2_kg

        summary_parts = []
        for key in counts:
            summary_parts.append(
                f"{counts[key]}x {key} emitting total {totals[key]:.2f}kg CO2"
            )
        return ", ".join(summary_parts)

    def _generate_rule_based_insight(self, actions: List[Action]) -> str:
        """Deterministic rule-based generator for weekly insights.

        Args:
            actions: List of Actions.

        Returns:
            A customized advice string.
        """
        # Calculate category totals
        transport_co2 = 0.0
        food_co2 = 0.0
        energy_co2 = 0.0

        car_count = 0
        flight_count = 0
        meat_count = 0
        ac_hours = 0.0

        for a in actions:
            if a.category == "transport":
                transport_co2 += a.co2_kg
                if a.type == "car":
                    car_count += 1
                elif a.type == "flight":
                    flight_count += 1
            elif a.category == "food":
                food_co2 += a.co2_kg
                if a.type == "meat-heavy":
                    meat_count += 1
            elif a.category == "energy":
                energy_co2 += a.co2_kg
                if a.type == "ac":
                    ac_hours += a.amount

        total_co2 = transport_co2 + food_co2 + energy_co2

        if total_co2 == 0.0:
            return (
                "Amazing job! You have logged activities but generated zero carbon emissions "
                "this week. Keep walking, biking, and maintaining this sustainable lifestyle!"
            )

        # Find the category with the highest emission
        max_cat = max(
            [("transport", transport_co2), ("food", food_co2), ("energy", energy_co2)],
            key=lambda x: x[1]
        )[0]

        if max_cat == "transport":
            if flight_count > 0:
                return (
                    f"Your flights contributed {transport_co2:.1f}kg CO2 this week. "
                    "Since aviation has a massive carbon density, offsetting your flights or "
                    "substituting short trips with high-speed rail is your top lever for reduction."
                )
            if car_count > 0:
                return (
                    f"You logged {car_count} car trips this week, making transport your highest "
                    f"emission source at {transport_co2:.1f}kg CO2. Shifting just two of those trips "
                    "to public transit, biking, or walking will reduce your footprint significantly."
                )
            return (
                f"Transport is your highest carbon contributor at {transport_co2:.1f}kg CO2. "
                "Try consolidating your errands or carpooling to lower your weekly commute emissions."
            )

        if max_cat == "food":
            if meat_count > 0:
                return (
                    f"You enjoyed meat-heavy meals {meat_count} times this week, putting your food "
                    f"footprint at {food_co2:.1f}kg CO2. Shifting to vegetarian or mixed meals just "
                    "a few days a week is a highly effective way to cut down your emissions."
                )
            return (
                f"Your dining choices contributed {food_co2:.1f}kg CO2. Emphasizing locally "
                "sourced, seasonal, plant-based ingredients is your best path to reduce food emissions."
            )

        # energy is highest
        if ac_hours > 0.0:
            return (
                f"Your air conditioning ran for {ac_hours:.1f} hours, driving your energy emissions "
                f"to {energy_co2:.1f}kg CO2. Raising your AC thermostat by just 2 degrees or using a fan "
                "can decrease your cooling emissions by up to 15%."
            )
        return (
            f"Household energy consumption was your main emissions driver at {energy_co2:.1f}kg CO2. "
            "Consider unplugging standby electronics and switching to energy-efficient appliances to "
            "reduce baseline electricity usage."
        )
