import pytest
from fastapi.testclient import TestClient

from callsup_platform.config import Settings
from callsup_platform.main import create_app


@pytest.fixture
def settings(tmp_path):
    db_path = tmp_path / "platform_test.db"
    return Settings(
        callsup_platform_env="test",
        callsup_platform_db_dsn=f"sqlite:///{db_path}",
        callsup_platform_redis_url="redis://localhost:6379/1",
        callsup_platform_s3_bucket="callsup-platform-test",
        callsup_platform_vector_namespace="callsup-platform-test",
        callsup_platform_vault_encryption_key_ref="vault://kv/data/callsup/platform/test-key",
        callsup_platform_tls_required=True,
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client

