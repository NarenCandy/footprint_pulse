"""Unit tests for Action model and ActionRepository.

Covers to_dict(), thread-safe concurrent access, and all repository methods
to push action.py coverage above 95%.
"""

import threading
from datetime import datetime, timezone
from app.models.action import Action, ActionRepository


def _make_action(co2_kg: float = 1.0, category: str = "transport") -> Action:
    return Action(
        id="abc",
        category=category,
        type="car",
        amount=10.0,
        unit="km",
        co2_kg=co2_kg,
        nudge="test nudge",
        timestamp=datetime.now(timezone.utc),
    )


# ── Action.to_dict ────────────────────────────────────────────────────────────

def test_action_to_dict_keys() -> None:
    action = _make_action()
    d = action.to_dict()
    assert set(d.keys()) == {"id", "category", "type", "amount", "unit", "co2_kg", "nudge", "timestamp"}


def test_action_to_dict_timestamp_is_isoformat() -> None:
    action = _make_action()
    d = action.to_dict()
    # Should parse back without error
    datetime.fromisoformat(d["timestamp"])


def test_action_to_dict_values() -> None:
    action = _make_action(co2_kg=2.5, category="food")
    d = action.to_dict()
    assert d["co2_kg"] == 2.5
    assert d["category"] == "food"


# ── ActionRepository basic ops ────────────────────────────────────────────────

def test_repository_add_and_get_all() -> None:
    repo = ActionRepository()
    a = _make_action(1.0)
    repo.add(a)
    assert len(repo.get_all()) == 1


def test_repository_get_all_sorted_descending() -> None:
    repo = ActionRepository()
    t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    a1 = Action("1", "transport", "car", 1, "km", 1.0, "n", t1)
    a2 = Action("2", "food", "veg", 1, "meals", 0.5, "n", t2)
    repo.add(a1)
    repo.add(a2)
    result = repo.get_all()
    assert result[0].id == "2"  # newer first


def test_repository_clear() -> None:
    repo = ActionRepository()
    repo.add(_make_action())
    repo.clear()
    assert repo.get_all() == []


def test_repository_get_total_co2() -> None:
    repo = ActionRepository()
    repo.add(_make_action(co2_kg=2.0))
    repo.add(_make_action(co2_kg=3.5))
    assert repo.get_total_co2() == 5.5


def test_repository_get_total_co2_empty() -> None:
    repo = ActionRepository()
    assert repo.get_total_co2() == 0.0


def test_repository_get_category_totals() -> None:
    repo = ActionRepository()
    repo.add(_make_action(co2_kg=1.0, category="transport"))
    repo.add(_make_action(co2_kg=2.0, category="food"))
    repo.add(_make_action(co2_kg=0.5, category="energy"))
    totals = repo.get_category_totals()
    assert totals["transport"] == 1.0
    assert totals["food"] == 2.0
    assert totals["energy"] == 0.5


def test_repository_get_category_totals_unknown_category() -> None:
    """Unknown category keys are added dynamically."""
    repo = ActionRepository()
    a = _make_action(co2_kg=3.0, category="other")
    repo.add(a)
    totals = repo.get_category_totals()
    assert totals["other"] == 3.0


# ── Thread-lock concurrent access ─────────────────────────────────────────────

def test_concurrent_add_is_thread_safe() -> None:
    """500 threads simultaneously adding actions must all persist."""
    repo = ActionRepository()
    threads = [threading.Thread(target=repo.add, args=(_make_action(1.0),)) for _ in range(500)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(repo.get_all()) == 500


def test_concurrent_get_all_while_adding() -> None:
    """Concurrent reads during writes must not raise exceptions."""
    repo = ActionRepository()
    errors = []

    def add_actions() -> None:
        for _ in range(100):
            repo.add(_make_action(1.0))

    def read_actions() -> None:
        for _ in range(100):
            try:
                repo.get_all()
            except Exception as e:
                errors.append(e)

    writers = [threading.Thread(target=add_actions) for _ in range(5)]
    readers = [threading.Thread(target=read_actions) for _ in range(5)]
    for t in writers + readers:
        t.start()
    for t in writers + readers:
        t.join()
    assert errors == []


def test_concurrent_get_total_co2_accuracy() -> None:
    """Total CO2 must be accurate after concurrent adds."""
    repo = ActionRepository()
    n = 200
    threads = [threading.Thread(target=repo.add, args=(_make_action(1.0),)) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert repo.get_total_co2() == float(n)


def test_concurrent_clear_and_add() -> None:
    """clear() racing with add() must not raise."""
    repo = ActionRepository()
    errors = []

    def add_loop() -> None:
        for _ in range(50):
            repo.add(_make_action(1.0))

    def clear_loop() -> None:
        for _ in range(50):
            try:
                repo.clear()
            except Exception as e:
                errors.append(e)

    t1 = threading.Thread(target=add_loop)
    t2 = threading.Thread(target=clear_loop)
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert errors == []
