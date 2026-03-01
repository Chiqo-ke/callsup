import tempfile

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings(
            data_dir=temp_dir,
            enforce_tls_in_transit=False,
            allow_insecure_http=True,
            encryption_key="hEKxY8Q_9l8UlDc6HBs2jJm8UhjKxB95idQ2YG9kgSc=",
        )
        app = create_app(settings)
        with TestClient(app) as test_client:
            yield test_client

