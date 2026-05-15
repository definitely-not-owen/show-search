from pathlib import Path

import pytest

from show_search.state import State, StateCorruptError


def test_load_missing_file_yields_empty_state(tmp_path: Path):
    s = State.load(tmp_path / "seen.json")
    assert not s.contains("anything")


def test_add_then_contains_round_trips_through_disk(tmp_path: Path):
    path = tmp_path / "seen.json"
    s = State.load(path)
    s.add("abc123")
    s.save()

    reloaded = State.load(path)
    assert reloaded.contains("abc123")


def test_forget_removes_id(tmp_path: Path):
    path = tmp_path / "seen.json"
    s = State.load(path)
    s.add("abc123")
    assert s.forget("abc123") is True
    assert s.forget("abc123") is False
    assert not s.contains("abc123")


def test_corrupt_file_raises(tmp_path: Path):
    path = tmp_path / "seen.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(StateCorruptError):
        State.load(path)
