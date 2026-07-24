"""Happy-path coverage for the first vertical slice:

find an artist -> open a performance -> mark attendance / add a song ->
see the contribution and revision history.
"""

from datetime import date

from tests.conftest import as_user


def _create_performance(client, artist_id, venue="Fendika", performed_on=None):
    return client.post(
        "/api/v1/performances",
        headers=as_user("fan"),
        json={
            "artist_id": artist_id,
            "venue": venue,
            "city": "Addis Ababa",
            "performed_on": (performed_on or date(2023, 5, 1)).isoformat(),
        },
    )


def test_find_artist(client, seeded):
    resp = client.get("/api/v1/artists", params={"q": "aster"})
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Aster Aweke"


def test_full_slice(client, seeded):
    artist_id = seeded["artist"].id

    # Open a performance (create then read it back).
    created = _create_performance(client, artist_id)
    assert created.status_code == 201, created.text
    perf_id = created.json()["id"]

    opened = client.get(f"/api/v1/performances/{perf_id}")
    assert opened.status_code == 200
    assert opened.json()["venue"] == "Fendika"

    # Mark attendance.
    att = client.post(f"/api/v1/performances/{perf_id}/attendance", headers=as_user("fan"))
    assert att.status_code == 200
    assert att.json() == {
        "performance_id": perf_id,
        "attending": True,
        "attendance_count": 1,
    }

    # Add one missing song.
    song = client.post(
        f"/api/v1/performances/{perf_id}/songs",
        headers=as_user("fan"),
        json={"title": "Tizita"},
    )
    assert song.status_code == 201, song.text
    assert song.json()["song_title"] == "Tizita"
    assert song.json()["position"] == 1

    # See the contribution and revision history.
    history = client.get(f"/api/v1/performances/{perf_id}/revisions")
    assert history.status_code == 200
    actions = {r["action"] for r in history.json()}
    assert {"create"} <= actions
    summaries = " ".join(r["summary"] for r in history.json())
    assert "Tizita" in summaries


def test_attendance_is_idempotent(client, seeded):
    perf_id = _create_performance(client, seeded["artist"].id).json()["id"]
    for _ in range(3):
        resp = client.post(f"/api/v1/performances/{perf_id}/attendance", headers=as_user("fan"))
    assert resp.json()["attendance_count"] == 1

    # Un-marking is a soft removal.
    off = client.delete(f"/api/v1/performances/{perf_id}/attendance", headers=as_user("fan"))
    assert off.json()["attendance_count"] == 0


def test_duplicate_song_rejected(client, seeded):
    perf_id = _create_performance(client, seeded["artist"].id).json()["id"]
    body = {"title": "Tizita"}
    assert (
        client.post(
            f"/api/v1/performances/{perf_id}/songs", headers=as_user("fan"), json=body
        ).status_code
        == 201
    )
    dup = client.post(f"/api/v1/performances/{perf_id}/songs", headers=as_user("fan"), json=body)
    assert dup.status_code == 409
    assert dup.json()["code"] == "duplicate_song"


def test_contribution_requires_auth(client, seeded):
    # No X-User header -> server-side authorisation rejects the write.
    resp = client.post(
        "/api/v1/performances",
        json={
            "artist_id": seeded["artist"].id,
            "venue": "X",
            "city": "Y",
            "performed_on": "2023-01-01",
        },
    )
    assert resp.status_code == 401
