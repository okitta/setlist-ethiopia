"""Anti-harassment and anti-fabrication rules — unit and API level."""

from datetime import date, timedelta

import pytest

from app.moderation import (
    ModerationError,
    PerformanceFacts,
    check_performance_plausibility,
    screen_text,
)
from tests.conftest import as_user


# --- Unit: harassment screening -------------------------------------------
def test_screen_allows_clean_text():
    screen_text("Great show, amazing energy!", field="notes")  # no exception


@pytest.mark.parametrize("bad", ["kill yourself", "you should die", "K Y S"])
def test_screen_blocks_harassment(bad):
    with pytest.raises(ModerationError) as exc:
        screen_text(bad, field="notes")
    assert exc.value.code == "harassment_blocked"


# --- Unit: fabrication guards ---------------------------------------------
def test_future_performance_rejected():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ModerationError) as exc:
        check_performance_plausibility(
            PerformanceFacts(tomorrow, "Venue", "City"),
            today=date.today(),
            earliest_year=1930,
        )
    assert exc.value.code == "future_performance"


def test_absurd_past_rejected():
    with pytest.raises(ModerationError) as exc:
        check_performance_plausibility(
            PerformanceFacts(date(1800, 1, 1), "Venue", "City"),
            today=date.today(),
            earliest_year=1930,
        )
    assert exc.value.code == "implausible_date"


# --- API level -------------------------------------------------------------
def test_create_rejects_future_show(client, seeded):
    tomorrow = date.today() + timedelta(days=1)
    resp = client.post(
        "/api/v1/performances",
        headers=as_user("fan"),
        json={
            "artist_id": seeded["artist"].id,
            "venue": "Fendika",
            "city": "Addis Ababa",
            "performed_on": tomorrow.isoformat(),
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "future_performance"


def test_create_rejects_harassing_notes(client, seeded):
    resp = client.post(
        "/api/v1/performances",
        headers=as_user("fan"),
        json={
            "artist_id": seeded["artist"].id,
            "venue": "Fendika",
            "city": "Addis Ababa",
            "performed_on": "2023-05-01",
            "notes": "kill yourself",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "harassment_blocked"


def test_duplicate_performance_rejected(client, seeded):
    body = {
        "artist_id": seeded["artist"].id,
        "venue": "Fendika",
        "city": "Addis Ababa",
        "performed_on": "2023-05-01",
    }
    assert client.post("/api/v1/performances", headers=as_user("fan"), json=body).status_code == 201
    dup = client.post("/api/v1/performances", headers=as_user("fan"), json=body)
    assert dup.status_code == 409
    assert dup.json()["code"] == "duplicate_performance"


def test_report_and_curator_archive(client, seeded):
    perf_id = client.post(
        "/api/v1/performances",
        headers=as_user("fan"),
        json={
            "artist_id": seeded["artist"].id,
            "venue": "Fendika",
            "city": "Addis Ababa",
            "performed_on": "2023-05-01",
        },
    ).json()["id"]

    # A fan reports a fabricated record.
    report = client.post(
        "/api/v1/reports",
        headers=as_user("fan"),
        json={"entity_type": "performance", "entity_id": perf_id, "reason": "fabricated"},
    )
    assert report.status_code == 201

    # A contributor cannot archive (server-side authorisation).
    forbidden = client.post(f"/api/v1/performances/{perf_id}/archive", headers=as_user("fan"))
    assert forbidden.status_code == 403

    # A curator can, and history is preserved (record still resolvable via revisions).
    archived = client.post(f"/api/v1/performances/{perf_id}/archive", headers=as_user("curator"))
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True

    # Archived performance disappears from public view but its history remains.
    assert client.get(f"/api/v1/performances/{perf_id}").status_code == 404
    revisions = client.get(f"/api/v1/performances/{perf_id}/revisions").json()
    assert any(r["action"] == "archive" for r in revisions)
