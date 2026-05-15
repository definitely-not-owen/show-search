from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from .models import Event

log = logging.getLogger("show_search.scrape")

REGION_URL = "https://19hz.info/eventlisting_{region}.php"
USER_AGENT = "show-search/0.1 (+https://github.com/local/show-search)"
TIMEOUT_S = 20

ISO_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)
VENUE_RE = re.compile(r"@\s*(?P<venue>.+?)\s*(?:\((?P<hood>[^)]+)\))?\s*$")
PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")


class ScrapeError(Exception):
    pass


def fetch_region(region: str, session: Optional[requests.Session] = None) -> str:
    s = session or requests.Session()
    url = REGION_URL.format(region=region)
    try:
        resp = s.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
    except requests.RequestException as e:
        raise ScrapeError(f"fetch failed: {e}") from e
    if resp.status_code != 200:
        raise ScrapeError(f"fetch non-200: {resp.status_code}")
    return resp.text


def parse_events(html: str, today: date) -> list[Event]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[Event] = []
    seen_ids: set[str] = set()
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            if row.find("th") is not None:
                continue
            cells = row.find_all("td", recursive=True)
            if len(cells) < 7:
                continue
            try:
                event = _parse_row(cells, today)
            except _SkipRow as e:
                log.warning("parse_skip reason=%s", e)
                continue
            if event is None:
                continue
            if event.id in seen_ids:
                continue
            seen_ids.add(event.id)
            events.append(event)
    return events


class _SkipRow(Exception):
    pass


def _parse_row(cells: list[Tag], today: date) -> Optional[Event]:
    iso_text = cells[6].get_text(" ", strip=True)
    parsed_date = _parse_iso_date(iso_text)
    if parsed_date is None:
        raise _SkipRow("missing_iso_date")

    date_cell_text = cells[0].get_text(" ", strip=True)
    parsed_time = _parse_time(date_cell_text)

    title, url, venue, neighborhood = _parse_title_cell(cells[1])
    if not title:
        raise _SkipRow("missing_title")

    genres_text = cells[2].get_text(" ", strip=True)
    genres = [g.strip().lower() for g in re.split(r"[,/]", genres_text) if g.strip()]

    price_age_text = cells[3].get_text(" ", strip=True)
    price, age = _parse_price_age(price_age_text)

    return Event(
        title=title,
        venue=venue,
        neighborhood=neighborhood,
        date=parsed_date,
        time=parsed_time,
        genres=genres,
        price=price,
        age=age,
        url=url,
    )


def _parse_iso_date(text: str) -> Optional[date]:
    m = ISO_DATE_RE.search(text)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _parse_time(text: str) -> Optional[str]:
    m = TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3).lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def _parse_title_cell(cell: Tag) -> tuple[str, str, str, str]:
    a = cell.find("a")
    if a is not None:
        title = a.get_text(" ", strip=True)
        url = a.get("href", "")
        tail = _text_after(cell, a)
    else:
        full = cell.get_text(" ", strip=True)
        head, _, tail = full.partition("@")
        title = head.strip()
        url = ""
        tail = "@" + tail if tail else ""
    venue, neighborhood = _parse_venue(tail)
    return title, url, venue, neighborhood


def _text_after(cell: Tag, anchor: Tag) -> str:
    parts: list[str] = []
    found = False
    for child in cell.children:
        if not found:
            if child is anchor:
                found = True
            continue
        if isinstance(child, NavigableString):
            parts.append(str(child))
            continue
        if isinstance(child, Tag) and child.name == "td":
            break
    return " ".join(parts).strip()


def _parse_venue(text: str) -> tuple[str, str]:
    text = text.lstrip("@ ").strip()
    if not text:
        return "", ""
    m = VENUE_RE.match("@ " + text)
    if not m:
        return text, ""
    venue = (m.group("venue") or "").strip()
    hood = (m.group("hood") or "").strip()
    return venue, hood


def _parse_price_age(text: str) -> tuple[Optional[int], Optional[str]]:
    if not text:
        return None, None
    parts = [p.strip() for p in text.split("|")]
    price: Optional[int] = None
    age: Optional[str] = None
    for part in parts:
        if not part:
            continue
        if "free" in part.lower() and price is None:
            price = 0
            continue
        m = PRICE_RE.search(part)
        if m and price is None:
            price = int(float(m.group(1)))
            continue
        if age is None and part:
            age = part
    return price, age
