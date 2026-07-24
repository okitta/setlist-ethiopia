"""Test fixtures: an isolated in-memory database and a TestClient.

Each test run uses its own SQLite database created directly from the model
metadata, so tests never touch a real environment.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Artist, Role, User


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(db_session):
    """A contributor, a curator, and one artist."""
    contributor = User(handle="fan", display_name="Fan", role=Role.contributor)
    curator = User(handle="curator", display_name="Curator", role=Role.curator)
    artist = Artist(name="Aster Aweke", slug="aster-aweke")
    db_session.add_all([contributor, curator, artist])
    db_session.commit()
    return {"contributor": contributor, "curator": curator, "artist": artist}


def as_user(handle: str) -> dict:
    return {"X-User": handle}
