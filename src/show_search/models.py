from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Event:
    title: str
    venue: str
    neighborhood: str
    date: date
    time: Optional[str]
    genres: list[str]
    price: Optional[int]
    age: Optional[str]
    url: str

    @property
    def id(self) -> str:
        key = f"{self.date.isoformat()}|{self.title.strip().lower()}|{self.venue.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


@dataclass
class Preferences:
    regions: list[str]
    genres: list[str] = field(default_factory=list)
    artists: list[str] = field(default_factory=list)
    free_days: list[str] = field(default_factory=list)
    price_max: Optional[int] = None
    horizon_days: int = 30
    venue_blocklist: list[str] = field(default_factory=list)
    venue_allowlist: list[str] = field(default_factory=list)
    neighborhoods: list[str] = field(default_factory=list)


@dataclass
class Match:
    event: Event
    matched_on: list[str]
