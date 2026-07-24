"""User-Agent compliance (MusicBrainz requires a meaningful, non-anonymous UA)."""

import pytest

from ethioscrape.http import PoliteClient, build_user_agent

# The exact User-Agent strings MusicBrainz treats as "anonymous" and throttles.
_ANONYMOUS = {"", "Java", "Python-urllib", "Jakarta Commons-HttpClient", "Apache-HttpClient"}


def test_user_agent_matches_recommended_format():
    ua = build_user_agent("me@example.com")
    # "Application/version ( contact )"
    assert ua.startswith("SetlistEthiopiaScraper/")
    assert " ( " in ua and ua.endswith(" )")
    assert "me@example.com" in ua


def test_default_user_agent_is_not_anonymous():
    assert build_user_agent() not in _ANONYMOUS
    assert "github.com/okitta/setlist-ethiopia" in build_user_agent()


def test_client_sets_the_header():
    client = PoliteClient(contact="me@example.com")
    assert "SetlistEthiopiaScraper" in client.session.headers["User-Agent"]
    assert "me@example.com" in client.session.headers["User-Agent"]


class _Resp:
    status_code = 200

    def json(self):
        return {"ok": True}


def test_api_calls_can_bypass_robots_but_html_still_honours_it(monkeypatch):
    client = PoliteClient(min_interval=0)
    # Pretend robots.txt disallows everything on this host.
    monkeypatch.setattr(client, "_allowed", lambda url: False)
    monkeypatch.setattr(client.session, "get", lambda *a, **k: _Resp())

    url = "https://musicbrainz.org/ws/2/artist"
    # Default (HTML scraping) path is blocked by robots.txt...
    with pytest.raises(PermissionError):
        client.get_json(url)
    # ...but documented-API calls opt out and succeed.
    assert client.get_json(url, check_robots=False) == {"ok": True}
