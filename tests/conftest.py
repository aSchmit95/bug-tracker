import threading
import time
from pathlib import Path
from unittest.mock import patch as mock_patch

import pytest
from fastapi.testclient import TestClient

SAMPLE_BUG = {
    "title":               "Login button unresponsive on Safari",
    "description":         "Clicking the login button does nothing on Safari 17.",
    "steps_to_reproduce":  "1. Open Safari\n2. Go to /login\n3. Click Login",
    "expected_result":     "User is redirected to dashboard",
    "actual_result":       "Nothing happens, no error shown",
    "severity":            "high",
    "reporter":            "alex",
}

E2E_PORT = 8766


# ─── Backend fixture ──────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, mocker):
    """TestClient with an isolated temp DB, wiped after each test."""
    mocker.patch("database.DB_PATH", str(tmp_path / "test.db"))
    import main
    with TestClient(main.app) as c:
        yield c


# ─── E2E fixture ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    """Real uvicorn server for Playwright tests."""
    db_path = str(tmp_path_factory.mktemp("e2e_db") / "test.db")

    with mock_patch("database.DB_PATH", db_path):
        import database
        database.init_db()

        import uvicorn
        import main
        config = uvicorn.Config(main.app, host="127.0.0.1", port=E2E_PORT, log_level="error")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        import httpx
        for _ in range(30):
            try:
                httpx.get(f"http://127.0.0.1:{E2E_PORT}/api/bugs", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

        yield f"http://127.0.0.1:{E2E_PORT}"

        server.should_exit = True
        time.sleep(0.2)
