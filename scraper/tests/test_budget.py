"""Tests for the daily budget guard and the API-key check (no network)."""

import json

from ethioscrape import fixtures
from ethioscrape.budget import DailyBudget
from ethioscrape.http import FetchError
from ethioscrape.sources import setlistfm


class _FakeClient:
    """Stands in for PoliteClient; returns one setlist page per call."""

    def __init__(self):
        self.calls = 0

    def get_json(self, url, headers=None, params=None, check_robots=True):
        self.calls += 1
        return {"setlist": fixtures.SFM_SETLISTS[:1], "itemsPerPage": 20, "total": 1}


def test_budget_stops_requests_at_limit(tmp_path):
    budget = DailyBudget(tmp_path / "usage.json", limit=2)
    client = _FakeClient()
    setlistfm.collect(
        client, "key", artist_mbids=["a", "b", "c", "d", "e"], max_pages=1, budget=budget
    )
    assert client.calls == 2  # stopped after the 2-request daily cap
    assert budget.used == 2
    assert budget.remaining == 0


def test_budget_persists_across_instances(tmp_path):
    path = tmp_path / "usage.json"
    DailyBudget(path, 1440).spend(5)
    reopened = DailyBudget(path, 1440)
    assert reopened.used == 5
    assert reopened.remaining == 1435


def test_budget_resets_on_new_day(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"date": "2000-01-01", "used": 999}))
    fresh = DailyBudget(path, 1440)
    assert fresh.used == 0  # stale day ignored


def test_check_api_key_success():
    class C:
        def get_json(self, *a, **k):
            return {"total": 2, "artist": [{"name": "Mulatu Astatke"}, {"name": "X"}]}

    result = setlistfm.check_api_key(C(), "key")
    assert result["ok"] and result["total"] == 2
    assert "Mulatu Astatke" in result["sample"]


def test_check_api_key_invalid():
    class C:
        def get_json(self, *a, **k):
            raise FetchError("HTTP 401", status=401)

    result = setlistfm.check_api_key(C(), "bad")
    assert result["ok"] is False and result["status"] == 401
