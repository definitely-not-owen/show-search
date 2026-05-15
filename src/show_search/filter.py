from __future__ import annotations

import re
from datetime import date, timedelta

from .models import Event, Match, Preferences

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def apply(events: list[Event], prefs: Preferences, today: date) -> list[Match]:
    horizon_end = today + timedelta(days=prefs.horizon_days)
    matches: list[Match] = []
    block = {v.lower() for v in prefs.venue_blocklist}
    allow = {v.lower() for v in prefs.venue_allowlist}
    neighborhoods = {n.lower() for n in prefs.neighborhoods}
    genres = [g.lower() for g in prefs.genres]
    artists = [a.lower() for a in prefs.artists]
    free_days = {d.lower() for d in prefs.free_days}

    for e in events:
        if e.date < today or e.date > horizon_end:
            continue
        if block and e.venue.lower() in block:
            continue
        if allow and e.venue.lower() not in allow:
            continue
        if neighborhoods and e.neighborhood.lower() not in neighborhoods:
            continue

        matched_on: list[str] = []

        if genres or artists:
            genre_hit = _genre_match(e.genres, genres) if genres else None
            artist_hit = _artist_match(e.title, artists) if artists else None
            if not genre_hit and not artist_hit:
                continue
            if genre_hit:
                matched_on.append(f"genre:{genre_hit}")
            if artist_hit:
                matched_on.append(f"artist:{artist_hit}")

        if free_days:
            dow = _DAY_NAMES[e.date.weekday()]
            if dow not in free_days:
                continue
            matched_on.append(f"day:{dow}")

        if prefs.price_max is not None:
            if e.price is not None and e.price > prefs.price_max:
                continue
            matched_on.append(f"price<={prefs.price_max}")

        matches.append(Match(event=e, matched_on=matched_on))
    return matches


def _genre_match(event_genres: list[str], wanted: list[str]) -> str | None:
    for w in wanted:
        for eg in event_genres:
            if w in eg:
                return w
    return None


def _artist_match(title: str, wanted: list[str]) -> str | None:
    haystack = title.lower()
    for w in wanted:
        pattern = r"\b" + re.escape(w) + r"\b"
        if re.search(pattern, haystack):
            return w
    return None
