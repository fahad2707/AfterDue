import pytest
from fastapi.testclient import TestClient

from tests.conftest import build_app
from tests.unit.conftest import UNIT_ENV


@pytest.fixture
def keyed_client():
    """App that enforces the shared proxy secret."""
    with TestClient(build_app(**{**UNIT_ENV, "INTERNAL_API_KEY": "test-secret"})) as c:
        yield c


def test_api_rejects_missing_internal_key(keyed_client):
    assert keyed_client.get("/api/meta").status_code == 401


def test_api_accepts_valid_internal_key(keyed_client):
    r = keyed_client.get("/api/meta", headers={"x-internal-api-key": "test-secret"})
    assert r.status_code == 200


def test_health_endpoints_bypass_internal_key(keyed_client):
    """Railway's healthcheck cannot send the secret."""
    assert keyed_client.get("/healthz").status_code == 200
    assert keyed_client.get("/readyz").status_code == 503
