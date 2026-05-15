from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .models import Preferences

VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


class ConfigError(Exception):
    pass


CONFIG_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["region"],
    "properties": {
        "region": {"type": "string", "description": "19hz regional slug, e.g. 'BayArea'."},
        "genres": {"type": "array", "items": {"type": "string"}, "default": []},
        "free_days": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(VALID_DAYS)},
            "default": [],
        },
        "price_max": {"type": ["integer", "null"], "default": None},
        "horizon_days": {"type": "integer", "minimum": 1, "default": 30},
        "venue_blocklist": {"type": "array", "items": {"type": "string"}, "default": []},
        "venue_allowlist": {"type": "array", "items": {"type": "string"}, "default": []},
        "neighborhoods": {"type": "array", "items": {"type": "string"}, "default": []},
    },
    "additionalProperties": False,
}


def load_config(path: Path) -> Preferences:
    if not path.exists():
        raise ConfigError(f"config not found: {path}")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"config parse error in {path}: {e}") from e

    if "region" not in raw or not isinstance(raw["region"], str):
        raise ConfigError("config missing required string field 'region'")

    free_days = raw.get("free_days", [])
    bad = [d for d in free_days if d not in VALID_DAYS]
    if bad:
        raise ConfigError(f"config free_days has invalid day(s): {bad}; valid: {sorted(VALID_DAYS)}")

    return Preferences(
        region=raw["region"],
        genres=list(raw.get("genres", [])),
        free_days=list(free_days),
        price_max=raw.get("price_max"),
        horizon_days=int(raw.get("horizon_days", 30)),
        venue_blocklist=list(raw.get("venue_blocklist", [])),
        venue_allowlist=list(raw.get("venue_allowlist", [])),
        neighborhoods=list(raw.get("neighborhoods", [])),
    )
