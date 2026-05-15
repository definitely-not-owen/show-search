# show-search

A lightweight CLI that crawls [19hz.info](https://19hz.info) and emits **new** electronic music events matching your preferences. Designed to be invoked by an AI agent (OpenClaw, OpenHermes, similar) on its heartbeat — the agent owns the user-comms channel; this tool is just a sensor.

## How it fits

```
┌─────────────────┐  heartbeat   ┌──────────────┐   HTTP    ┌────────────┐
│ OpenClaw / etc. │ ───────────▶ │ show-search  │ ────────▶ │ 19hz.info  │
│  (your agent)   │ ◀─────────── │   check      │           └────────────┘
└─────────────────┘   JSON of                 │
        │             NEW matches             │ updates
        ▼                                     ▼
   text / email                          ~/.local/state/
   (whatever the                         show-search/seen.json
   agent uses)
```

The agent runs `show-search check` whenever it wants. We return only events the agent hasn't seen yet, so the agent can blindly forward anything we emit to the user.

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+ (for `tomllib` in stdlib).

## Quick start

```bash
show-search init --region BayArea           # writes ~/.config/show-search/config.toml
$EDITOR ~/.config/show-search/config.toml   # set genres, days, price ceiling
show-search check                            # JSON of new matches to stdout
```

Example output:

```json
[
  {
    "id": "8785a6cadd79",
    "title": "Solomun, Notre Dame",
    "venue": "Pier 48 Shed A",
    "neighborhood": "San Francisco",
    "date": "2026-05-15",
    "time": "18:00",
    "genres": ["tech house", "deep house"],
    "price": null,
    "age": "21+",
    "url": "https://www.axs.com/events/1382129/solomun-tickets",
    "matched_on": ["genre:house", "day:fri"]
  }
]
```

## Configuration

`~/.config/show-search/config.toml`:

```toml
region = "BayArea"                # 19hz regional slug — see https://19hz.info for the full list
genres = ["techno", "dnb", "jungle", "house"]
free_days = ["fri", "sat"]        # day-of-week filter; omit to allow any day
price_max = 40                    # USD ceiling; omit for unlimited; null-priced events pass through
horizon_days = 30                 # only consider events within N days
venue_blocklist = ["The Midway"]
venue_allowlist = []              # if non-empty, ONLY these venues
neighborhoods = []                # filter on neighborhood field if you want
```

For the machine-readable JSON Schema (so an agent can help a user edit this):

```bash
show-search describe
```

## Agent integration

On each heartbeat, the agent runs:

```bash
show-search check
```

- **stdout** — JSON array of new matches (possibly `[]`)
- **stderr** — `key=value` diagnostics, e.g. `error=http_fetch region=BayArea reason=...`
- **exit codes**:
  - `0` success (possibly empty array)
  - `2` scrape failure — state is **not** mutated, retry safely on the next heartbeat
  - `3` config error — surface to the user; don't keep retrying

Pseudocode for an agent loop (OpenClaw/Hermes-style):

```python
import json, subprocess

proc = subprocess.run(["show-search", "check"], capture_output=True, text=True)

if proc.returncode == 0:
    for m in json.loads(proc.stdout):
        notify_user(
            f"{m['title']} @ {m['venue']} on {m['date']} "
            f"({m['time'] or 'time TBA'})"
            f"{f", ${m['price']}" if m['price'] is not None else ''}. "
            f"Why I think you'd like it: {', '.join(m['matched_on'])}. "
            f"{m['url']}"
        )
elif proc.returncode == 2:
    log.warning("show-search transient failure: %s", proc.stderr)
elif proc.returncode == 3:
    notify_user("show-search config error — please fix.")
```

Because `check` only mutates state on success, the agent can call it as often as it likes without losing events to transient network failures.

To re-surface an event the user wants to be reminded about:

```bash
show-search seen --forget 8785a6cadd79
```

## Commands

| Command | Purpose | Exit codes |
|---|---|---|
| `show-search init` | Write a starter config | 0, 1 |
| `show-search describe` | Print config JSON Schema | 0 |
| `show-search check` | Emit NEW matches; update state | 0, 2, 3 |
| `show-search list` | Emit ALL current matches; no state touch | 0, 2, 3 |
| `show-search seen --forget <id>` | Drop an id from state | 0, 1 |

`show-search check --dry-run` emits matches but skips the state update.

## Testing

```bash
pytest           # offline tests (uses a frozen 19hz HTML fixture)
pytest -m live   # also hits real 19hz; opt-in
```
