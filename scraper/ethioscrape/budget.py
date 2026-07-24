"""A persistent per-day request budget.

setlist.fm caps usage at 1440 requests/day. This tracks how many setlist.fm requests
we've made *today* (UTC) across runs in a small JSON state file, so repeated
invocations in the same day don't blow the cap and get the key rate-limited.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyBudget:
    def __init__(self, path: str | pathlib.Path, limit: int) -> None:
        self.path = pathlib.Path(path)
        self.limit = limit
        self._date = _today()
        self._used = 0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        # Only carry over the count if the stored day is still today.
        if data.get("date") == self._date:
            self._used = int(data.get("used", 0))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"date": self._date, "used": self._used}), encoding="utf-8"
        )

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self._used)

    def can_spend(self, n: int = 1) -> bool:
        return self._used + n <= self.limit

    def spend(self, n: int = 1) -> None:
        self._used += n
        self._save()
