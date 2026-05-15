import json
from datetime import date
from pathlib import Path

import pytest

from show_search.state import NEVER_PRUNE, State, StateCorruptError


def test_load_missing_file_yields_empty_state(tmp_path: Path):
    s = State.load(tmp_path / "seen.json")
    assert not s.contains("anything")


def test_add_then_contains_round_trips_through_disk(tmp_path: Path):
    path = tmp_path / "seen.json"
    s = State.load(path)
    s.add("abc123", date(2026, 6, 1))
    s.save()

    reloaded = State.load(path)
    assert reloaded.contains("abc123")
    assert reloaded.seen["abc123"] == "2026-06-01"


def test_forget_removes_id(tmp_path: Path):
    path = tmp_path / "seen.json"
    s = State.load(path)
    s.add("abc123", date(2026, 6, 1))
    assert s.forget("abc123") is True
    assert s.forget("abc123") is False
    assert not s.contains("abc123")


def test_corrupt_file_raises(tmp_path: Path):
    path = tmp_path / "seen.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(StateCorruptError):
        State.load(path)


def test_prune_past_drops_events_before_today(tmp_path: Path):
    path = tmp_path / "seen.json"
    s = State.load(path)
    s.add("past", date(2026, 1, 1))
    s.add("today", date(2026, 5, 15))
    s.add("future", date(2026, 12, 31))
    pruned = s.prune_past(date(2026, 5, 15))
    assert pruned == 1
    assert not s.contains("past")
    assert s.contains("today")
    assert s.contains("future")


def test_legacy_float_state_is_preserved_but_never_pruned(tmp_path: Path):
    path = tmp_path / "seen.json"
    path.write_text(json.dumps({"seen": {"legacy_id": 1234567890.0}, "last_updated": 0}),
                    encoding="utf-8")
    s = State.load(path)
    assert s.contains("legacy_id")
    assert s.seen["legacy_id"] == NEVER_PRUNE
    pruned = s.prune_past(date(2026, 5, 15))
    assert pruned == 0
    assert s.contains("legacy_id")
