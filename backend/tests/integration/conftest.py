import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from tests.conftest import build_app, read_env_file_value

COLLECTIONS = [
    "customers",
    "subscriptions",
    "invoices",
    "events",
    "audit_logs",
    "recovery_cases",
    "simulation_runs",
    "model_runs",
]


@pytest.fixture(scope="session")
def mongo_uri() -> str:
    uri = os.environ.get("RECLAIM_TEST_MONGODB_URI") or read_env_file_value("MONGODB_URI")
    if not uri:
        pytest.skip("no MONGODB_URI configured; integration tests need Atlas")
    return uri


@pytest.fixture(scope="session")
def test_db_name() -> str:
    """A throwaway database per session. Never the real `reclaim` database."""
    return f"reclaim_test_{uuid4().hex[:10]}"


@pytest.fixture(scope="session")
def client(mongo_uri: str, test_db_name: str, tmp_path_factory):
    artifact = tmp_path_factory.mktemp("model") / "recovery_model.joblib"
    app = build_app(
        APP_ENV="test",
        LOG_LEVEL="WARNING",
        MONGODB_URI=mongo_uri,
        MONGODB_DB=test_db_name,
        INTERNAL_API_KEY="",
        LLM_ENABLED="false",
        MODEL_ARTIFACT_PATH=str(artifact),
    )
    # Entering TestClient runs the lifespan, which connects Mongo and creates
    # the indexes the ledger depends on for correctness.
    with TestClient(app) as c:
        yield c

    MongoClient(mongo_uri).drop_database(test_db_name)


@pytest.fixture(autouse=True)
def clean_collections(mongo_uri: str, test_db_name: str, client):
    """Empty the ledger before each test but keep the indexes.

    Dropping the database per test would also drop the unique indexes, and
    several tests exist precisely to prove those indexes do their job.
    """
    db = MongoClient(mongo_uri)[test_db_name]
    for name in COLLECTIONS:
        db[name].delete_many({})
    yield
