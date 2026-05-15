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
    "anyOf": [
        {"required": ["region"]},
        {"required": ["regions"]},
    ],
    "properties": {
        "region": {
            "type": "string",
            "description": "Single 19hz regional slug. Accepted for backwards compat; prefer `regions`.",
        },
        "regions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "One or more 19hz regional slugs, e.g. ['BayArea', 'LosAngeles'].",
        },
        "genres": {"type": "array", "items": {"type": "string"}, "default": []},
        "artists": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Artist names; word-boundary substring match against event title. Matches OR with genres.",
        },
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

    regions = _resolve_regions(raw)

    free_days = raw.get("free_days", [])
    bad = [d for d in free_days if d not in VALID_DAYS]
    if bad:
        raise ConfigError(f"config free_days has invalid day(s): {bad}; valid: {sorted(VALID_DAYS)}")

    return Preferences(
        regions=regions,
        genres=list(raw.get("genres", [])),
        artists=list(raw.get("artists", [])),
        free_days=list(free_days),
        price_max=raw.get("price_max"),
        horizon_days=int(raw.get("horizon_days", 30)),
        venue_blocklist=list(raw.get("venue_blocklist", [])),
        venue_allowlist=list(raw.get("venue_allowlist", [])),
        neighborhoods=list(raw.get("neighborhoods", [])),
    )


def _resolve_regions(raw: dict) -> list[str]:
    if "regions" in raw:
        regions = raw["regions"]
        if not isinstance(regions, list) or not all(isinstance(r, str) for r in regions):
            raise ConfigError("config 'regions' must be a list of strings")
        if not regions:
            raise ConfigError("config 'regions' must not be empty")
        return list(regions)
    if "region" in raw:
        if not isinstance(raw["region"], str):
            raise ConfigError("config 'region' must be a string")
        return [raw["region"]]
    raise ConfigError("config missing required field: one of 'region' or 'regions'")
