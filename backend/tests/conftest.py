import importlib
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def read_env_file_value(key: str) -> str | None:
    """Read one key out of the repo-root .env without importing app settings.

    Integration tests need the real Atlas URI, but the app's Settings object is
    lru_cached and the unit suite deliberately blanks the URI. Reading the file
    directly keeps the two suites from fighting over process state.
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}=") and not line.startswith("#"):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


def build_app(**env: str):
    """Rebuild the FastAPI app under a specific environment.

    Settings are cached and `app.main` reads some of them at import time, so
    changing configuration between test suites requires clearing the cache and
    reloading the module. Doing it in one helper keeps that fragility in a
    single place.
    """
    for key, value in env.items():
        os.environ[key] = value

    import app.config

    app.config.get_settings.cache_clear()

    import app.main

    return importlib.reload(app.main).app
