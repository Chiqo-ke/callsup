from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    callsup_platform_package: str = "svc-platform"
    callsup_platform_env: str = "dev"
    callsup_platform_db_dsn: str = "sqlite:///./callsup_platform.db"
    callsup_platform_redis_url: str = "redis://localhost:6379/0"
    callsup_platform_s3_bucket: str = "callsup-platform-local"
    callsup_platform_vector_namespace: str = "callsup-platform-default"
    callsup_platform_vault_encryption_key_ref: str = "vault://kv/data/callsup/platform/encryption"
    callsup_platform_tls_required: bool = True
    callsup_platform_external_endpoint: str = "mock://provider/platform"

    @field_validator("callsup_platform_vault_encryption_key_ref")
    @classmethod
    def validate_vault_reference(cls, value: str) -> str:
        if not value.startswith("vault://"):
            raise ValueError("Vault-only secret references are required")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

