from pathlib import Path

import pytest

from show_search.config import (
    CONFIG_JSON_SCHEMA,
    ConfigError,
    load_config,
)


def write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_minimal_config(tmp_path: Path):
    p = write(tmp_path / "c.toml", 'region = "BayArea"\n')
    cfg = load_config(p)
    assert cfg.region == "BayArea"
    assert cfg.genres == []
    assert cfg.horizon_days == 30


def test_full_config(tmp_path: Path):
    body = """
region = "BayArea"
genres = ["techno", "dnb"]
free_days = ["fri", "sat"]
price_max = 40
horizon_days = 14
venue_blocklist = ["X"]
venue_allowlist = []
neighborhoods = ["SoMa"]
"""
    cfg = load_config(write(tmp_path / "c.toml", body))
    assert cfg.genres == ["techno", "dnb"]
    assert cfg.free_days == ["fri", "sat"]
    assert cfg.price_max == 40
    assert cfg.horizon_days == 14
    assert cfg.venue_blocklist == ["X"]
    assert cfg.neighborhoods == ["SoMa"]


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")


def test_missing_region_raises(tmp_path: Path):
    p = write(tmp_path / "c.toml", "genres = []\n")
    with pytest.raises(ConfigError, match="region"):
        load_config(p)


def test_bad_day_name_raises(tmp_path: Path):
    p = write(tmp_path / "c.toml", 'region = "BayArea"\nfree_days = ["funday"]\n')
    with pytest.raises(ConfigError, match="free_days"):
        load_config(p)


def test_schema_has_required_keys():
    assert CONFIG_JSON_SCHEMA["required"] == ["region"]
    assert "genres" in CONFIG_JSON_SCHEMA["properties"]
