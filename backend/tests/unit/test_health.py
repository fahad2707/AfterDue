def test_healthz_is_up_without_dependencies(client):
    """Liveness must succeed even when Mongo is unreachable, otherwise a DB
    blip makes the platform kill a process that is actually fine."""
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "reclaim-backend"
    assert body["uptime_seconds"] >= 0


def test_readyz_reports_unready_when_mongo_absent(client):
    """Readiness must fail loudly rather than pretend, so a bad deploy never
    receives traffic."""
    r = client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False
    assert body["checks"]["mongodb"]["ok"] is False
    assert body["checks"]["mongodb"]["detail"]


def test_meta_endpoint_flags_synthetic_data(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["synthetic"] is True
    assert body["llm_enabled"] is False
    assert body["policy_version"] == "v1"
