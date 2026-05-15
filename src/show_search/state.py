from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

NEVER_PRUNE = "9999-12-31"


class StateCorruptError(Exception):
    pass


@dataclass
class State:
    path: Path
    seen: dict[str, str] = field(default_factory=dict)   # id -> event_date ISO (YYYY-MM-DD)

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls(path=path, seen={})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StateCorruptError(f"{path}: {e}") from e
        seen_raw = raw.get("seen") or {}
        if not isinstance(seen_raw, dict):
            raise StateCorruptError(f"{path}: 'seen' must be an object")
        seen: dict[str, str] = {}
        for k, v in seen_raw.items():
            if isinstance(v, str):
                seen[str(k)] = v
            else:
                # legacy float timestamp; keep but never auto-prune
                seen[str(k)] = NEVER_PRUNE
        return cls(path=path, seen=seen)

    def contains(self, event_id: str) -> bool:
        return event_id in self.seen

    def add(self, event_id: str, event_date: date) -> None:
        self.seen.setdefault(event_id, event_date.isoformat())

    def forget(self, event_id: str) -> bool:
        return self.seen.pop(event_id, None) is not None

    def prune_past(self, today: date) -> int:
        """Drop entries for events whose date is strictly before today. Returns count pruned."""
        cutoff = today.isoformat()
        before = len(self.seen)
        self.seen = {k: v for k, v in self.seen.items() if v >= cutoff}
        return before - len(self.seen)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"seen": self.seen, "last_updated": time.time()}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)
