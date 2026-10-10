import os
from collections.abc import Generator

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CERTIFICATES_DIR", "./tmp_certificates")
os.environ.setdefault("PROCESSING_MODE", "sync")
os.environ.setdefault("MAX_RECIPIENTS_PER_JOB", "1000")

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, create_db_and_tables, get_db
from app.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    create_db_and_tables()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
