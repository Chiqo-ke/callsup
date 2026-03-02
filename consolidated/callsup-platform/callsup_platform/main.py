import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import create_session_factory, create_sqlalchemy_engine, initialize_database, is_database_ready
from .logging import configure_logging
from .metrics import ONBOARDING_COUNTER, REQUEST_LATENCY, metrics_response
from .schemas import BusinessCreate, ResourceManifest
from .services import ExternalProvisioningClient, create_business, get_manifest


def create_app(settings: Settings | None = None) -> FastAPI:
    service_settings = settings or get_settings()
    logger = logging.getLogger("callsup_platform")
    configure_logging(service_settings)
    engine = create_sqlalchemy_engine(service_settings)
    session_factory = create_session_factory(engine)
    external_client = ExternalProvisioningClient()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(engine)
        yield

    app = FastAPI(title="CALLSUP Platform API", version="v0.1.0", lifespan=lifespan)

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @app.middleware("http")
    async def track_latency(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        REQUEST_LATENCY.labels(path=request.url.path).observe(time.perf_counter() - started)
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": "svc-platform", "version": "v0.1.0"}

    @app.get("/readyz")
    def readyz():
        try:
            ready = is_database_ready(engine)
            if ready:
                return {"status": "ready", "db": "ok", "tls_required": service_settings.callsup_platform_tls_required}
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"db not ready: {exc}") from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="service not ready")

    @app.get("/metrics")
    def metrics():
        return metrics_response()

    @app.post("/platform/business", response_model=ResourceManifest, status_code=status.HTTP_201_CREATED)
    def onboard_business(payload: BusinessCreate, session: Session = Depends(get_session)):
        try:
            manifest = create_business(session, payload, service_settings, external_client)
            logger.info(
                "business onboarded",
                extra={"event": "platform.onboarding.created", "business_id": payload.business_id, "request_id": None},
            )
            ONBOARDING_COUNTER.labels(status="success").inc()
            return manifest
        except ValueError as exc:
            ONBOARDING_COUNTER.labels(status="conflict").inc()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.get("/platform/business/{business_id}", response_model=ResourceManifest)
    def business_manifest(business_id: str, session: Session = Depends(get_session)):
        try:
            return get_manifest(session, business_id, service_settings)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return app


app = create_app()

