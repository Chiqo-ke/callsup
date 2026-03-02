def test_health_and_readiness(client):
    health = client.get("/healthz")
    ready = client.get("/readyz")
    assert health.status_code == 200
    assert ready.status_code == 200
    assert health.json()["version"] == "v0.1.0"


def test_onboarding_and_fetch_manifest(client):
    payload = {
        "business_id": "biz-123",
        "name": "Biz 123",
        "summary": "contact admin@biz.com",
        "rules_doc": "dial +1 212 555 9000",
    }
    created = client.post("/platform/business", json=payload)
    assert created.status_code == 201
    manifest = created.json()
    assert manifest["business_id"] == "biz-123"
    assert manifest["db_name"] == "callsup_platform_biz-123"

    fetched = client.get("/platform/business/biz-123")
    assert fetched.status_code == 200
    assert fetched.json()["vector_namespace"].endswith(":biz-123")

    duplicate = client.post("/platform/business", json=payload)
    assert duplicate.status_code == 409


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "callsup_platform_onboarding_total" in response.text

