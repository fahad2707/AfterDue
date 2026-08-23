import pytest
from fastapi.testclient import TestClient

from tests.conftest import build_app

UNIT_ENV = {
    "APP_ENV": "test",
    "LOG_LEVEL": "WARNING",
    "MONGODB_URI": "",
    "INTERNAL_API_KEY": "",
    "LLM_ENABLED": "false",
}


@pytest.fixture
def client():
    """App with no database. Everything here must pass without Mongo."""
    with TestClient(build_app(**UNIT_ENV)) as c:
        yield c
