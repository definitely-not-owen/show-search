import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from show_search import cli


def _write_config(tmp_path: Path, body: str = 'region = "BayArea"\n') -> Path:
    p = tmp_path / "c.toml"
    p.write_text(body, encoding="utf-8")
    return p


SAMPLE_HTML = """
<table>
<tr><th>D</th><th>E</th><th>T</th><th>P</th><th>O</th><th>L</th><th>i</th></tr>
<tr>
  <td>Sat: May 23 (10pm)</td>
  <td><a href="https://x/1">Surgeon</a> @ Great Northern (SoMa)<td>techno</td><td>$35 | 21+</td><td>Org</td><td></td><td>2026/05/23</td>
</tr>
</table>
"""

SAMPLE_HTML_LA = """
<table>
<tr><th>D</th><th>E</th><th>T</th><th>P</th><th>O</th><th>L</th><th>i</th></tr>
<tr>
  <td>Sun: May 24 (10pm)</td>
  <td><a href="https://x/2">Hodge</a> @ Resident (DTLA)<td>techno</td><td>$30 | 21+</td><td>Org</td><td></td><td>2026/05/24</td>
</tr>
</table>
"""


def _common(state: Path, extra=()):
    return ["--config", "x", "--state", str(state),
            "--cache-dir", str(state.parent / "cache"),
            "--no-cache", *extra]


def test_describe_emits_schema(capsys):
    rc = cli.main(["describe"])
    out = capsys.readouterr().out
    schema = json.loads(out)
    assert rc == 0
    assert "regions" in schema["properties"]


def test_check_outputs_matches_and_updates_state(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state),
                       "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert len(payload) == 1
    assert payload[0]["title"] == "Surgeon"
    assert payload[0]["date"] == "2026-05-23"
    assert payload[0]["region"] == "BayArea"
    assert state.exists()

    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc2 = cli.main(["check", "--config", str(cfg), "--state", str(state),
                        "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert json.loads(out2) == []


def test_check_multi_region_dedupes(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path, 'regions = ["BayArea", "LosAngeles"]\n')
    state = tmp_path / "seen.json"
    fakes = {"BayArea": SAMPLE_HTML, "LosAngeles": SAMPLE_HTML_LA}

    def fake_fetch(region, **kw):
        return fakes[region]

    with patch("show_search.cli.fetch_region", side_effect=fake_fetch), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state),
                       "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    titles = sorted(m["title"] for m in payload)
    regions = sorted(m["region"] for m in payload)
    assert titles == ["Hodge", "Surgeon"]
    assert regions == ["BayArea", "LosAngeles"]


def test_check_prunes_past_events_from_state(tmp_path: Path):
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    state.write_text(json.dumps({
        "seen": {"old_id": "2025-01-01", "future_id": "2026-12-31"},
        "last_updated": 0,
    }), encoding="utf-8")
    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state),
                       "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    assert rc == 0
    final = json.loads(state.read_text())["seen"]
    assert "old_id" not in final
    assert "future_id" in final


def test_check_network_failure_exits_2_and_preserves_state(tmp_path: Path):
    from show_search.scrape import ScrapeError
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", side_effect=ScrapeError("boom")):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state),
                       "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    assert rc == 2
    assert not state.exists()


def test_check_missing_config_exits_3(tmp_path: Path):
    rc = cli.main(["check", "--config", str(tmp_path / "nope.toml"),
                   "--state", str(tmp_path / "s.json"),
                   "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    assert rc == 3


def test_list_does_not_update_state(tmp_path: Path):
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["list", "--config", str(cfg), "--state", str(state),
                       "--cache-dir", str(tmp_path / "cache"), "--no-cache"])
    assert rc == 0
    assert not state.exists()


def test_seen_forget(tmp_path: Path):
    state = tmp_path / "seen.json"
    state.write_text(json.dumps({"seen": {"abc123": "2026-12-01"},
                                 "last_updated": 0}), encoding="utf-8")
    rc = cli.main(["seen", "--forget", "abc123", "--state", str(state)])
    assert rc == 0
    assert "abc123" not in json.loads(state.read_text())["seen"]


def test_init_writes_starter_with_multiple_regions(tmp_path: Path):
    target = tmp_path / "c.toml"
    rc = cli.main(["init", "--config", str(target), "--non-interactive",
                   "--regions", "BayArea", "LosAngeles"])
    assert rc == 0
    body = target.read_text()
    assert '"BayArea"' in body
    assert '"LosAngeles"' in body


def test_init_back_compat_single_region(tmp_path: Path):
    target = tmp_path / "c.toml"
    rc = cli.main(["init", "--config", str(target), "--non-interactive",
                   "--region", "BayArea"])
    assert rc == 0
    assert '"BayArea"' in target.read_text()
