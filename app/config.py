import base64
import hashlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CALLSUP_AUDIO_ENGINE_", extra="ignore"
    )

    service_version: str = "0.1.0"
    log_level: str = "INFO"
    data_dir: str = "data"

    vault_api_key_ref: str = "vault://secret/data/callsup/audio-engine#api_key"
    vault_encryption_key_ref: str = (
        "vault://secret/data/callsup/audio-engine#encryption_key"
    )
    encryption_key: str | None = None
    openai_api_key: str | None = None   # used by Whisper transcription

    enforce_tls_in_transit: bool = True
    allow_insecure_http: bool = False

    def get_encryption_key(self) -> bytes:
        if self.encryption_key:
            return self.encryption_key.encode("utf-8")
        digest = hashlib.sha256(self.vault_encryption_key_ref.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

