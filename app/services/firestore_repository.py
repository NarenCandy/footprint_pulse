"""Firestore-backed action repository with in-memory fallback.

Attempts to use Google Cloud Firestore for persistence. If credentials,
project config, or the SDK are unavailable, falls back to the existing
in-memory ActionRepository transparently.
"""

import logging
import os
from typing import List
from app.models.action import Action, ActionRepository

logger = logging.getLogger(__name__)

_COLLECTION = "actions"


class FirestoreRepository:
    """Wraps ActionRepository with optional Firestore persistence."""

    def __init__(self) -> None:
        self._memory_repo = ActionRepository()
        self._db = None
        self._firestore_active = False
        self._try_init_firestore()

    def _try_init_firestore(self) -> None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
        if not project:
            logger.info("Firestore: GOOGLE_CLOUD_PROJECT not set — using in-memory fallback.")
            return
        try:
            from google.cloud import firestore  # type: ignore
            self._db = firestore.Client(project=project)
            self._firestore_active = True
            logger.info("Firestore client initialized for project '%s'.", project)
        except Exception as e:
            logger.warning("Firestore init failed (%s) — using in-memory fallback.", e)

    def is_active(self) -> bool:
        return self._firestore_active

    def add(self, action: Action) -> Action:
        self._memory_repo.add(action)
        if self._firestore_active:
            try:
                self._db.collection(_COLLECTION).document(action.id).set(action.to_dict())
            except Exception as e:
                logger.error("Firestore write failed (%s) — in-memory record kept.", e)
        return action

    def get_all(self) -> List[Action]:
        return self._memory_repo.get_all()

    def clear(self) -> None:
        self._memory_repo.clear()
        if self._firestore_active:
            try:
                docs = self._db.collection(_COLLECTION).stream()
                for doc in docs:
                    doc.reference.delete()
            except Exception as e:
                logger.error("Firestore clear failed (%s).", e)

    def get_total_co2(self) -> float:
        return self._memory_repo.get_total_co2()

    def get_category_totals(self):
        return self._memory_repo.get_category_totals()
