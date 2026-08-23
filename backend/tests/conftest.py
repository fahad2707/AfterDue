import os

import pytest

# Tests must never depend on a developer's local .env. Pin the environment
# before app modules are imported and settings get cached.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ["MONGODB_URI"] = ""
os.environ["INTERNAL_API_KEY"] = ""
os.environ["LLM_ENABLED"] = "false"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
