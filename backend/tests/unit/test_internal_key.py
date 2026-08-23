import importlib

import pytest


@pytest.fixture
def keyed_client(monkeypatch):
    """Boot a second app instance that enforces the shared proxy secret."""
    monkeypatch.setenv("INTERNAL_API_KEY", "test-secret")

    import app.config
    import app.main

    app.config.get_settings.cache_clear()
    main = importlib.reload(app.main)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as c:
        yield c

    app.config.get_settings.cache_clear()
    importlib.reload(app.main)


def test_api_rejects_missing_internal_key(keyed_client):
    assert keyed_client.get("/api/meta").status_code == 401


def test_api_accepts_valid_internal_key(keyed_client):
    r = keyed_client.get("/api/meta", headers={"x-internal-api-key": "test-secret"})
    assert r.status_code == 200


def test_health_endpoints_bypass_internal_key(keyed_client):
    """Railway's healthcheck cannot send the secret."""
    assert keyed_client.get("/healthz").status_code == 200
    assert keyed_client.get("/readyz").status_code == 503
