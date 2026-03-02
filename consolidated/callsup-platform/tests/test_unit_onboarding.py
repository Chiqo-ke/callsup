import pytest
from sqlalchemy.orm import Session

from callsup_platform.db import create_session_factory, create_sqlalchemy_engine, initialize_database
from callsup_platform.models import Business
from callsup_platform.schemas import BusinessCreate
from callsup_platform.services import ExternalProvisioningClient, create_business, get_manifest


class CapturingExternalClient(ExternalProvisioningClient):
    def __init__(self):
        self.last_payload = None

    def provision_business(self, payload: dict) -> dict:
        self.last_payload = payload
        return {"status": "ok"}


@pytest.fixture
def db_session(settings):
    engine = create_sqlalchemy_engine(settings)
    initialize_database(engine)
    factory = create_session_factory(engine)
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def test_create_business_encrypts_and_redacts(settings, db_session):
    payload = BusinessCreate(
        business_id="acme-1",
        name="Acme",
        summary="Owner email: owner@acme.com",
        rules_doc="Call +1 800 555 4444 first",
    )
    external = CapturingExternalClient()
    manifest = create_business(db_session, payload, settings, external)
    assert manifest.business_id == "acme-1"
    assert external.last_payload["summary"] == "Owner email: [REDACTED_EMAIL]"
    assert external.last_payload["rules_doc"] == "Call [REDACTED_PHONE] first"

    stored = db_session.get(Business, "acme-1")
    assert stored is not None
    assert b"owner@acme.com" not in (stored.encrypted_summary or b"")
    assert b"800" not in (stored.encrypted_rules_doc or b"")


def test_get_manifest_not_found(settings, db_session):
    with pytest.raises(LookupError):
        get_manifest(db_session, "missing", settings)

