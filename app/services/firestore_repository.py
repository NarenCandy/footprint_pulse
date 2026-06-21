"""Firestore-backed action repository with in-memory fallback.

Attempts to use Google Cloud Firestore for persistence. If credentials,
project config, or the SDK are unavailable, falls back to the existing
in-memory ActionRepository transparently.
"""

import logging
import os
from typing import Any

from app.models.action import Action, ActionRepository

logger = logging.getLogger(__name__)

_COLLECTION = "actions"


class FirestoreRepository:
    """Wraps ActionRepository with optional Firestore persistence.

    All public methods mirror ActionRepository so callers are unaware of
    which backend is active.
    """

    def __init__(self) -> None:
        """Initialises the repository and attempts to connect to Firestore."""
        self._memory_repo: ActionRepository = ActionRepository()
        self._db: Any | None = None
        self._firestore_active: bool = False
        self._try_init_firestore()

    def _try_init_firestore(self) -> None:
        """Attempts to initialise the Firestore client.

        Sets ``_firestore_active`` to True on success; leaves it False and
        logs a warning on any failure so the in-memory fallback remains active.
        """
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCLOUD_PROJECT"
        )
        if not project:
            logger.info(
                "Firestore: GOOGLE_CLOUD_PROJECT not set — using in-memory fallback."
            )
            return
        try:
            from google.cloud import firestore  # type: ignore[import-untyped]

            self._db = firestore.Client(project=project)
            self._firestore_active = True
            logger.info("Firestore client initialised for project '%s'.", project)
        except Exception as exc:
            logger.warning(
                "Firestore init failed (%s) — using in-memory fallback.", exc
            )

    def is_active(self) -> bool:
        """Returns True if Firestore is connected and being used.

        Returns:
            True when Firestore writes are active, False when in-memory only.
        """
        return self._firestore_active

    def add(self, action: Action) -> Action:
        """Adds an action to both in-memory store and Firestore (if active).

        Args:
            action: The Action instance to persist.

        Returns:
            The added Action.
        """
        self._memory_repo.add(action)
        if self._firestore_active and self._db is not None:
            try:
                self._db.collection(_COLLECTION).document(action.id).set(
                    action.to_dict()
                )
            except Exception as exc:
                logger.error(
                    "Firestore write failed (%s) — in-memory record kept.", exc
                )
        return action

    def get_all(self) -> list[Action]:
        """Retrieves all logged actions from the in-memory store.

        Returns:
            A list of Actions sorted by timestamp descending.
        """
        return self._memory_repo.get_all()

    def clear(self) -> None:
        """Clears all actions from the in-memory store and Firestore (if active)."""
        self._memory_repo.clear()
        if self._firestore_active and self._db is not None:
            try:
                docs = self._db.collection(_COLLECTION).stream()
                for doc in docs:
                    doc.reference.delete()
            except Exception as exc:
                logger.error("Firestore clear failed (%s).", exc)

    def get_total_co2(self) -> float:
        """Returns the total CO2 across all in-memory actions.

        Returns:
            Total CO2 in kilograms.
        """
        return self._memory_repo.get_total_co2()

    def get_category_totals(self) -> dict[str, float]:
        """Returns CO2 totals grouped by category from the in-memory store.

        Returns:
            A dictionary mapping category name to total CO2 in kg.
        """
        return self._memory_repo.get_category_totals()
