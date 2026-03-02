from fastapi import FastAPI

app = FastAPI(title="CALLSUP Knowledge & Ops", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/readiness")
def readiness() -> dict:
    return {"status": "ready"}
