from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .config import CONFIG_JSON_SCHEMA, ConfigError, load_config
from .filter import apply as filter_apply
from .models import Match, Preferences
from .scrape import DEFAULT_CACHE_TTL_S, ScrapeError, fetch_region, parse_events
from .state import State, StateCorruptError

DEFAULT_CONFIG = Path.home() / ".config" / "show-search" / "config.toml"
DEFAULT_STATE = Path.home() / ".local" / "state" / "show-search" / "seen.json"
DEFAULT_CACHE = Path.home() / ".cache" / "show-search"


def today() -> date:
    return date.today()


def _match_to_json(m: Match, region: Optional[str] = None) -> dict:
    e = m.event
    return {
        "id": e.id,
        "title": e.title,
        "venue": e.venue,
        "neighborhood": e.neighborhood,
        "date": e.date.isoformat(),
        "time": e.time,
        "genres": e.genres,
        "price": e.price,
        "age": e.age,
        "url": e.url,
        "region": region,
        "matched_on": m.matched_on,
    }


def _err(**kv) -> None:
    parts = " ".join(f"{k}={v}" for k, v in kv.items())
    print(parts, file=sys.stderr)


def _load_prefs(path: Path) -> Optional[Preferences]:
    try:
        return load_config(path)
    except ConfigError as e:
        _err(error="config", path=str(path), reason=str(e))
        return None


def _scrape_and_filter(
    prefs: Preferences, when: date, cache_dir: Optional[Path], ttl_s: int,
) -> Optional[list[tuple[Match, str]]]:
    """Return (match, region) pairs across all configured regions, deduped by event id."""
    out: list[tuple[Match, str]] = []
    seen_ids: set[str] = set()
    for region in prefs.regions:
        try:
            html = fetch_region(region, cache_dir=cache_dir, ttl_s=ttl_s)
        except ScrapeError as e:
            _err(error="http_fetch", region=region, reason=str(e))
            return None
        events = parse_events(html, today=when)
        for m in filter_apply(events, prefs, today=when):
            if m.event.id in seen_ids:
                continue
            seen_ids.add(m.event.id)
            out.append((m, region))
    return out


def _cache_args(args) -> tuple[Optional[Path], int]:
    if getattr(args, "no_cache", False):
        return None, 0
    return Path(args.cache_dir), int(args.cache_ttl_s)


def cmd_check(args) -> int:
    prefs = _load_prefs(Path(args.config))
    if prefs is None:
        return 3
    try:
        state = State.load(Path(args.state))
    except StateCorruptError:
        _err(error="state", path=str(args.state), reason="invalid_json")
        return 3

    when = today()
    state.prune_past(when)

    cache_dir, ttl_s = _cache_args(args)
    matches = _scrape_and_filter(prefs, when, cache_dir, ttl_s)
    if matches is None:
        return 2

    new = [(m, r) for (m, r) in matches if not state.contains(m.event.id)]
    print(json.dumps([_match_to_json(m, region=r) for (m, r) in new], indent=2))

    if not args.dry_run:
        for m, _r in new:
            state.add(m.event.id, m.event.date)
        state.save()
    return 0


def cmd_list(args) -> int:
    prefs = _load_prefs(Path(args.config))
    if prefs is None:
        return 3
    cache_dir, ttl_s = _cache_args(args)
    matches = _scrape_and_filter(prefs, today(), cache_dir, ttl_s)
    if matches is None:
        return 2
    print(json.dumps([_match_to_json(m, region=r) for (m, r) in matches], indent=2))
    return 0


def cmd_describe(_args) -> int:
    print(json.dumps(CONFIG_JSON_SCHEMA, indent=2))
    return 0


STARTER_CONFIG = """\
regions = [{regions}]
genres = []
artists = []
free_days = []
# price_max = 40
horizon_days = 30
venue_blocklist = []
venue_allowlist = []
neighborhoods = []
"""


def cmd_init(args) -> int:
    target = Path(args.config)
    if target.exists() and not args.force:
        _err(error="exists", path=str(target), hint="pass --force to overwrite")
        return 1
    regions_arg = args.regions
    if not regions_arg and args.region:
        regions_arg = [args.region]
    if not regions_arg and not args.non_interactive:
        raw = input("Regions (comma-separated, e.g. BayArea,LosAngeles): ").strip()
        regions_arg = [r.strip() for r in raw.split(",") if r.strip()]
    if not regions_arg:
        _err(error="region_required")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    quoted = ", ".join(f'"{r}"' for r in regions_arg)
    target.write_text(STARTER_CONFIG.format(regions=quoted), encoding="utf-8")
    print(f"wrote {target}")
    return 0


def cmd_seen(args) -> int:
    try:
        state = State.load(Path(args.state))
    except StateCorruptError:
        _err(error="state", path=str(args.state), reason="invalid_json")
        return 3
    if args.forget:
        ok = state.forget(args.forget)
        if not ok:
            _err(error="not_found", id=args.forget)
            return 1
        state.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="show-search")
    sub = p.add_subparsers(dest="cmd", required=True)

    def _add_common(sp):
        sp.add_argument("--config", default=str(DEFAULT_CONFIG))
        sp.add_argument("--state", default=str(DEFAULT_STATE))
        sp.add_argument("--cache-dir", default=str(DEFAULT_CACHE),
                        help=f"directory for HTML cache (default: {DEFAULT_CACHE})")
        sp.add_argument("--cache-ttl-s", type=int, default=DEFAULT_CACHE_TTL_S,
                        help=f"cache TTL in seconds (default: {DEFAULT_CACHE_TTL_S})")
        sp.add_argument("--no-cache", action="store_true",
                        help="bypass the HTTP cache for this call")

    p_check = sub.add_parser("check", help="emit NEW matches as JSON, update state")
    _add_common(p_check)
    p_check.add_argument("--dry-run", action="store_true",
                         help="emit matches but do not update state")
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list", help="emit ALL current matches; does not touch state")
    _add_common(p_list)
    p_list.set_defaults(func=cmd_list)

    p_desc = sub.add_parser("describe", help="print config JSON Schema")
    p_desc.set_defaults(func=cmd_describe)

    p_init = sub.add_parser("init", help="write a starter config file")
    p_init.add_argument("--config", default=str(DEFAULT_CONFIG))
    p_init.add_argument("--region", help="single region (back-compat shortcut)")
    p_init.add_argument("--regions", nargs="+", help="one or more region slugs")
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--non-interactive", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_seen = sub.add_parser("seen", help="inspect or edit the seen ledger")
    p_seen.add_argument("--state", default=str(DEFAULT_STATE))
    p_seen.add_argument("--forget", help="remove an event id from state")
    p_seen.set_defaults(func=cmd_seen)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
