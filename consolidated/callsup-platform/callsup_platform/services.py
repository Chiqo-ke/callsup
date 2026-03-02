from sqlalchemy.orm import Session

from .config import Settings
from .models import Business
from .schemas import BusinessCreate, ResourceManifest
from .security import encrypt_at_rest, redact_payload


class ExternalProvisioningClient:
    def provision_business(self, payload: dict) -> dict:
        return {"status": "mocked", "payload": payload}


def build_manifest(business_id: str, settings: Settings) -> ResourceManifest:
    return ResourceManifest(
        business_id=business_id,
        db_name=f"callsup_platform_{business_id}",
        vector_namespace=f"{settings.callsup_platform_vector_namespace}:{business_id}",
        s3_path=f"s3://{settings.callsup_platform_s3_bucket}/business/{business_id}",
        k8s_namespace=f"callsup-platform-{settings.callsup_platform_env}",
        secret_ref=settings.callsup_platform_vault_encryption_key_ref,
    )


def create_business(
    session: Session,
    payload: BusinessCreate,
    settings: Settings,
    external_client: ExternalProvisioningClient,
) -> ResourceManifest:
    existing = session.get(Business, payload.business_id)
    if existing:
        raise ValueError("business already exists")

    safe_payload = redact_payload(payload.model_dump())
    external_client.provision_business(safe_payload)

    record = Business(
        business_id=payload.business_id,
        name=payload.name,
        encrypted_summary=encrypt_at_rest(settings.callsup_platform_vault_encryption_key_ref, payload.summary),
        encrypted_rules_doc=encrypt_at_rest(settings.callsup_platform_vault_encryption_key_ref, payload.rules_doc),
    )
    session.add(record)
    session.commit()
    return build_manifest(payload.business_id, settings)


def get_manifest(session: Session, business_id: str, settings: Settings) -> ResourceManifest:
    existing = session.get(Business, business_id)
    if not existing:
        raise LookupError("business not found")
    return build_manifest(business_id, settings)

