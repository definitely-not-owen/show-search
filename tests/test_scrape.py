from datetime import date

from show_search.scrape import REGION_URL, parse_events


def test_region_url_format():
    assert REGION_URL.format(region="BayArea").endswith("eventlisting_BayArea.php")


def test_parse_real_fixture_returns_many_events(regional_html):
    region, html = regional_html
    events = parse_events(html, today=date(2026, 5, 15))
    assert len(events) >= 50, f"{region}: only got {len(events)}"


def test_parse_real_fixture_has_well_formed_events(regional_html):
    region, html = regional_html
    events = parse_events(html, today=date(2026, 5, 15))
    for e in events[:20]:
        assert e.title, f"{region}: empty title"
        assert e.venue, f"{region}: empty venue for {e.title!r}"
        assert isinstance(e.date, date)
        assert isinstance(e.genres, list)


def test_parse_synthetic_canonical_row():
    html = """
    <table>
    <tr><th>Date/Time</th><th>Event</th><th>Tags</th><th>Price|Age</th>
        <th>Org</th><th>Links</th><th>iso</th></tr>
    <tr>
      <td>Sat: May 23 <br/>(10pm-2am)</td>
      <td><a href="https://x.test/tix">Surgeon, Hodge</a> @ The Great Northern (SoMa)<td>techno, minimal</td><td>$35 | 21+</td><td>Org</td><td></td><td><div>2026/05/23</div></td>
    </tr>
    </table>
    """
    events = parse_events(html, today=date(2026, 1, 1))
    assert len(events) == 1
    e = events[0]
    assert e.title == "Surgeon, Hodge"
    assert e.venue == "The Great Northern"
    assert e.neighborhood == "SoMa"
    assert e.date == date(2026, 5, 23)
    assert e.time == "22:00"
    assert "techno" in e.genres
    assert "minimal" in e.genres
    assert e.price == 35
    assert e.age == "21+"
    assert e.url == "https://x.test/tix"


def test_parse_free_price():
    html = """
    <table>
    <tr><th>D</th><th>E</th><th>T</th><th>P</th><th>O</th><th>L</th><th>i</th></tr>
    <tr>
      <td>Sun: Jul 12 (4pm-8pm)</td>
      <td><a href="https://x/2">Park Show</a> @ Dolores Park (Mission)<td>house</td><td>free | all ages</td><td>Org</td><td></td><td>2026/07/12</td>
    </tr>
    </table>
    """
    events = parse_events(html, today=date(2026, 1, 1))
    assert events[0].price == 0
    assert events[0].age == "all ages"


def test_parse_missing_price_just_age():
    html = """
    <table>
    <tr><th>D</th><th>E</th><th>T</th><th>P</th><th>O</th><th>L</th><th>i</th></tr>
    <tr>
      <td>Sun: Jul 12 (4pm)</td>
      <td><a href="https://x/3">Show</a> @ Venue (SF)<td>house</td><td>21+</td><td>Org</td><td></td><td>2026/07/12</td>
    </tr>
    </table>
    """
    events = parse_events(html, today=date(2026, 1, 1))
    assert events[0].price is None
    assert events[0].age == "21+"


def test_parse_skips_rows_missing_iso_date():
    html = """
    <table>
    <tr><th>D</th><th>E</th><th>T</th><th>P</th><th>O</th><th>L</th><th>i</th></tr>
    <tr>
      <td>TBA</td>
      <td><a href="https://x/4">Mystery</a> @ TBA (SF)<td>techno</td><td>21+</td><td>Org</td><td></td><td></td>
    </tr>
    </table>
    """
    events = parse_events(html, today=date(2026, 1, 1))
    assert events == []
