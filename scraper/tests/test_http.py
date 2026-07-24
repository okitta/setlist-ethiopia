"""User-Agent compliance (MusicBrainz requires a meaningful, non-anonymous UA)."""

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
