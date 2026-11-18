import os

os.environ["BRGRBYTE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["BRGRBYTE_JWT_SECRET_KEY"] = "test-only-signing-secret-key-at-least-32"
os.environ["BRGRBYTE_ADMIN_USERNAME"] = "admin"
os.environ["BRGRBYTE_ADMIN_PASSWORD"] = "test-password-long-enough"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, get_db
from app.main import app

test_engine = engine
TestingSessionLocal = SessionLocal


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
