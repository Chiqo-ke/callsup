from pathlib import Path

from cryptography.fernet import Fernet

from app.models import TranscriptSegment


class AudioRepository:
    def __init__(self, data_dir: str, encryption_key: bytes) -> None:
        self._data_path = Path(data_dir) / "audio"
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(encryption_key)
        self._transcripts: dict[str, list[TranscriptSegment]] = {}

    def save_audio(self, conv_id: str, content: bytes) -> None:
        encrypted = self._fernet.encrypt(content)
        (self._data_path / f"{conv_id}.bin").write_bytes(encrypted)

    def save_transcript(self, conv_id: str, segments: list[TranscriptSegment]) -> None:
        self._transcripts[conv_id] = segments

    def get_transcript(self, conv_id: str) -> list[TranscriptSegment]:
        if conv_id not in self._transcripts:
            raise KeyError(conv_id)
        return self._transcripts[conv_id]

