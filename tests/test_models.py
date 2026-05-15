from datetime import date

from show_search.models import Event, Match, Preferences


def test_event_id_is_stable_across_construction():
    e1 = Event(
        title="Surgeon + Hodge",
        venue="The Great Northern",
        neighborhood="SoMa",
        date=date(2026, 5, 23),
        time="22:00",
        genres=["techno"],
        price=35,
        age="21+",
        url="https://19hz.info/x",
    )
    e2 = Event(
        title="Surgeon + Hodge",
        venue="The Great Northern",
        neighborhood="DIFFERENT",
        date=date(2026, 5, 23),
        time="DIFFERENT",
        genres=["different"],
        price=999,
        age="?",
        url="DIFFERENT",
    )
    assert e1.id == e2.id
    assert len(e1.id) == 12


def test_event_id_changes_when_core_fields_change():
    base = dict(
        title="A", venue="V", neighborhood="N", date=date(2026, 1, 1),
        time=None, genres=[], price=None, age=None, url="",
    )
    e_base = Event(**base)
    assert Event(**{**base, "title": "B"}).id != e_base.id
    assert Event(**{**base, "venue": "W"}).id != e_base.id
    assert Event(**{**base, "date": date(2026, 1, 2)}).id != e_base.id


def test_preferences_defaults():
    p = Preferences(region="BayArea")
    assert p.region == "BayArea"
    assert p.genres == []
    assert p.free_days == []
    assert p.price_max is None
    assert p.horizon_days == 30
    assert p.venue_blocklist == []
    assert p.venue_allowlist == []
    assert p.neighborhoods == []


def test_match_carries_reasons():
    e = Event(
        title="x", venue="y", neighborhood="", date=date(2026, 1, 1),
        time=None, genres=[], price=None, age=None, url="",
    )
    m = Match(event=e, matched_on=["genre:techno", "day:sat"])
    assert m.event is e
    assert m.matched_on == ["genre:techno", "day:sat"]
