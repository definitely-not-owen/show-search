from datetime import date, timedelta

from show_search.filter import apply
from show_search.models import Event, Preferences

TODAY = date(2026, 5, 15)


def ev(**kw) -> Event:
    base = dict(
        title="X", venue="V", neighborhood="N", date=TODAY + timedelta(days=7),
        time="22:00", genres=["techno"], price=20, age="21+", url="",
    )
    base.update(kw)
    return Event(**base)


def test_genre_match_substring_case_insensitive():
    prefs = Preferences(region="BayArea", genres=["TECHNO"])
    matches = apply([ev(genres=["minimal techno"])], prefs, today=TODAY)
    assert len(matches) == 1
    assert "genre:techno" in matches[0].matched_on


def test_genre_filter_excludes_non_matching():
    prefs = Preferences(region="BayArea", genres=["techno"])
    matches = apply([ev(genres=["house"])], prefs, today=TODAY)
    assert matches == []


def test_no_genre_filter_matches_anything():
    prefs = Preferences(region="BayArea")
    matches = apply([ev(genres=["polka"])], prefs, today=TODAY)
    assert len(matches) == 1


def test_day_filter():
    sat_event = ev(date=TODAY + timedelta(days=1))
    sun_event = ev(date=TODAY + timedelta(days=2))
    prefs = Preferences(region="BayArea", free_days=["sat"])
    matches = apply([sat_event, sun_event], prefs, today=TODAY)
    assert len(matches) == 1
    assert matches[0].event is sat_event
    assert "day:sat" in matches[0].matched_on


def test_price_max():
    prefs = Preferences(region="BayArea", price_max=30)
    matches = apply([ev(price=35), ev(price=20), ev(price=None)], prefs, today=TODAY)
    prices = [m.event.price for m in matches]
    assert 35 not in prices
    assert 20 in prices
    assert None in prices


def test_horizon():
    prefs = Preferences(region="BayArea", horizon_days=10)
    inside = ev(date=TODAY + timedelta(days=5))
    outside = ev(date=TODAY + timedelta(days=30))
    matches = apply([inside, outside], prefs, today=TODAY)
    assert [m.event for m in matches] == [inside]


def test_blocklist_excludes():
    prefs = Preferences(region="BayArea", venue_blocklist=["The Midway"])
    matches = apply([ev(venue="The Midway"), ev(venue="Public Works")], prefs, today=TODAY)
    assert [m.event.venue for m in matches] == ["Public Works"]


def test_allowlist_when_present_excludes_others():
    prefs = Preferences(region="BayArea", venue_allowlist=["Public Works"])
    matches = apply(
        [ev(venue="The Midway"), ev(venue="Public Works")],
        prefs, today=TODAY,
    )
    assert [m.event.venue for m in matches] == ["Public Works"]


def test_neighborhood_filter():
    prefs = Preferences(region="BayArea", neighborhoods=["SoMa"])
    matches = apply(
        [ev(neighborhood="SoMa"), ev(neighborhood="Mission")],
        prefs, today=TODAY,
    )
    assert [m.event.neighborhood for m in matches] == ["SoMa"]
