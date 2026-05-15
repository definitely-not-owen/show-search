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


def test_describe_emits_schema(capsys):
    rc = cli.main(["describe"])
    out = capsys.readouterr().out
    schema = json.loads(out)
    assert rc == 0
    assert schema["required"] == ["region"]


def test_check_outputs_matches_and_updates_state(tmp_path: Path, capsys):
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert len(payload) == 1
    assert payload[0]["title"] == "Surgeon"
    assert payload[0]["date"] == "2026-05-23"
    assert state.exists()

    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc2 = cli.main(["check", "--config", str(cfg), "--state", str(state)])
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert json.loads(out2) == []


def test_check_network_failure_exits_2_and_preserves_state(tmp_path: Path):
    from show_search.scrape import ScrapeError
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", side_effect=ScrapeError("boom")):
        rc = cli.main(["check", "--config", str(cfg), "--state", str(state)])
    assert rc == 2
    assert not state.exists()


def test_check_missing_config_exits_3(tmp_path: Path):
    rc = cli.main(["check", "--config", str(tmp_path / "nope.toml"),
                   "--state", str(tmp_path / "s.json")])
    assert rc == 3


def test_list_does_not_update_state(tmp_path: Path):
    cfg = _write_config(tmp_path)
    state = tmp_path / "seen.json"
    with patch("show_search.cli.fetch_region", return_value=SAMPLE_HTML), \
         patch("show_search.cli.today", return_value=date(2026, 5, 15)):
        rc = cli.main(["list", "--config", str(cfg), "--state", str(state)])
    assert rc == 0
    assert not state.exists()


def test_seen_forget(tmp_path: Path):
    state = tmp_path / "seen.json"
    state.write_text(json.dumps({"seen": {"abc123": 0}, "last_updated": 0}), encoding="utf-8")
    rc = cli.main(["seen", "--forget", "abc123", "--state", str(state)])
    assert rc == 0
    assert "abc123" not in json.loads(state.read_text())["seen"]


def test_init_writes_starter(tmp_path: Path):
    target = tmp_path / "c.toml"
    rc = cli.main(["init", "--config", str(target), "--non-interactive", "--region", "BayArea"])
    assert rc == 0
    assert "BayArea" in target.read_text()
