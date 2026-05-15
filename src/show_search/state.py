from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


class StateCorruptError(Exception):
    pass


@dataclass
class State:
    path: Path
    seen: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls(path=path, seen={})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StateCorruptError(f"{path}: {e}") from e
        seen = raw.get("seen") or {}
        if not isinstance(seen, dict):
            raise StateCorruptError(f"{path}: 'seen' must be an object")
        return cls(path=path, seen={str(k): float(v) for k, v in seen.items()})

    def contains(self, event_id: str) -> bool:
        return event_id in self.seen

    def add(self, event_id: str) -> None:
        self.seen.setdefault(event_id, time.time())

    def forget(self, event_id: str) -> bool:
        return self.seen.pop(event_id, None) is not None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"seen": self.seen, "last_updated": time.time()}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)
