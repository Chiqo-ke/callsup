from app.transcription import transcribe_audio


def test_transcribe_audio_redacts_before_third_party():
    captured = {}

    def fake_third_party(payload: str):
        captured["payload"] = payload
        return [{"speaker": "customer", "text": payload, "confidence": 0.9}]

    segments = transcribe_audio(
        business_id="biz-1",
        conv_id="conv-1",
        audio_bytes=b"My email is me@example.com and phone is 415-555-0188",
        third_party_transcriber=fake_third_party,
    )

    assert len(segments) == 1
    assert "me@example.com" not in captured["payload"]
    assert "415-555-0188" not in captured["payload"]
    assert "[REDACTED_EMAIL]" in segments[0].text
    assert "[REDACTED_PHONE]" in segments[0].text

