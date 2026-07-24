"""The public data-reuse API: reusable, licensed, and free of personal data."""

from tests.conftest import as_user


def _make_perf_with_attendance(client, artist_id):
    perf_id = client.post(
        "/api/v1/performances",
        headers=as_user("fan"),
        json={
            "artist_id": artist_id,
            "venue": "Fendika",
            "city": "Addis Ababa",
            "performed_on": "2023-05-01",
        },
    ).json()["id"]
    client.post(f"/api/v1/performances/{perf_id}/attendance", headers=as_user("fan"))
    client.post(
        f"/api/v1/performances/{perf_id}/songs",
        headers=as_user("fan"),
        json={"title": "Tizita"},
    )
    return perf_id


def test_license_is_advertised(client):
    resp = client.get("/api/v1/public/license")
    assert resp.status_code == 200
    body = resp.json()
    assert body["license"] == "CC-BY-SA-4.0"
    assert "attribution" in body


def test_public_artists_carry_license_meta(client, seeded):
    resp = client.get("/api/v1/public/artists")
    assert resp.status_code == 200
    assert resp.json()["meta"]["license"] == "CC-BY-SA-4.0"
    assert any(a["name"] == "Aster Aweke" for a in resp.json()["data"])


def test_public_performance_has_no_personal_data(client, seeded):
    perf_id = _make_perf_with_attendance(client, seeded["artist"].id)
    resp = client.get(f"/api/v1/public/performances/{perf_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Attendance is exposed only as an aggregate count, never who attended.
    assert data["attendance_count"] == 1
    body_text = resp.text.lower()
    assert "fan" not in body_text  # no contributor handle leaks
    assert "user" not in body_text
    assert data["setlist"] == [{"position": 1, "song": "Tizita"}]


def test_public_api_hides_archived_records(client, seeded):
    perf_id = _make_perf_with_attendance(client, seeded["artist"].id)
    client.post(f"/api/v1/performances/{perf_id}/archive", headers=as_user("curator"))
    assert client.get(f"/api/v1/public/performances/{perf_id}").status_code == 404


def test_public_api_is_read_only(client, seeded):
    # There is no public write verb; POST to a public path is not allowed.
    resp = client.post("/api/v1/public/artists")
    assert resp.status_code == 405
