from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


ONBOARDING_COUNTER = Counter("callsup_platform_onboarding_total", "Total onboarding requests", ["status"])
REQUEST_LATENCY = Histogram("callsup_platform_request_latency_seconds", "Request latency", ["path"])


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

