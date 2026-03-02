from prometheus_client import Counter, Histogram, make_asgi_app

AUDIO_INGEST_REQUESTS = Counter(
    "callsup_audio_ingest_requests_total",
    "Count of audio ingest requests",
)
TRANSCRIPT_FETCH_REQUESTS = Counter(
    "callsup_audio_transcript_requests_total",
    "Count of transcript retrieval requests",
)
INGEST_PROCESSING_SECONDS = Histogram(
    "callsup_audio_ingest_processing_seconds",
    "Time spent processing ingest requests",
)

metrics_app = make_asgi_app()

