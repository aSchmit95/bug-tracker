"""
Backend integration tests for the Bug Tracker API.
Each test gets a fresh isolated SQLite database via the `client` fixture.
"""

import pytest
from conftest import SAMPLE_BUG


def create(client, **overrides):
    """Helper: POST a bug and return the response."""
    return client.post("/api/bugs", json={**SAMPLE_BUG, **overrides})


# ─── CRUD ─────────────────────────────────────────────────────────────────────

class TestBugCRUD:

    def test_list_empty_initially(self, client):
        res = client.get("/api/bugs")
        assert res.status_code == 200
        assert res.json() == []

    def test_create_returns_201_and_correct_fields(self, client):
        res = create(client)
        assert res.status_code == 201
        data = res.json()
        assert data["title"]    == SAMPLE_BUG["title"]
        assert data["severity"] == SAMPLE_BUG["severity"]
        assert data["reporter"] == SAMPLE_BUG["reporter"]
        assert data["status"]   == "open"
        assert data["id"] is not None

    def test_bug_listed_after_creation(self, client):
        create(client)
        bugs = client.get("/api/bugs").json()
        assert len(bugs) == 1
        assert bugs[0]["title"] == SAMPLE_BUG["title"]

    def test_get_single_bug(self, client):
        bug_id = create(client).json()["id"]
        res = client.get(f"/api/bugs/{bug_id}")
        assert res.status_code == 200
        assert res.json()["id"] == bug_id

    def test_get_nonexistent_bug_returns_404(self, client):
        assert client.get("/api/bugs/9999").status_code == 404

    def test_update_bug_title(self, client):
        bug_id = create(client).json()["id"]
        res = client.patch(f"/api/bugs/{bug_id}", json={"title": "Updated title"})
        assert res.status_code == 200
        assert res.json()["title"] == "Updated title"

    def test_update_nonexistent_bug_returns_404(self, client):
        assert client.patch("/api/bugs/9999", json={"title": "x"}).status_code == 404

    def test_delete_bug(self, client):
        bug_id = create(client).json()["id"]
        assert client.delete(f"/api/bugs/{bug_id}").status_code == 200
        assert client.get("/api/bugs").json() == []

    def test_delete_nonexistent_returns_404(self, client):
        assert client.delete("/api/bugs/9999").status_code == 404

    def test_newest_bug_listed_first(self, client):
        create(client, title="First")
        second_id = create(client, title="Second").json()["id"]
        assert client.get("/api/bugs").json()[0]["id"] == second_id


# ─── Validation ───────────────────────────────────────────────────────────────

class TestValidation:

    def test_create_without_title_returns_422(self, client):
        res = client.post("/api/bugs", json={**SAMPLE_BUG, "title": ""})
        # FastAPI/Pydantic returns 422 for missing required fields
        assert res.status_code in (400, 422)

    def test_create_with_invalid_severity_returns_422(self, client):
        res = create(client, severity="extreme")
        assert res.status_code == 422

    def test_filter_with_invalid_status_returns_422(self, client):
        assert client.get("/api/bugs?status=banana").status_code == 422

    def test_filter_with_invalid_severity_returns_422(self, client):
        assert client.get("/api/bugs?severity=banana").status_code == 422


# ─── Filters ──────────────────────────────────────────────────────────────────

class TestFilters:

    def test_filter_by_status(self, client):
        create(client)                                     # open by default
        create(client)
        # move one to in_progress
        bug_id = client.get("/api/bugs").json()[0]["id"]
        client.patch(f"/api/bugs/{bug_id}", json={"status": "in_progress"})

        open_bugs = client.get("/api/bugs?status=open").json()
        assert len(open_bugs) == 1

        in_progress = client.get("/api/bugs?status=in_progress").json()
        assert len(in_progress) == 1

    def test_filter_by_severity(self, client):
        create(client, severity="critical")
        create(client, severity="low")
        create(client, severity="low")

        assert len(client.get("/api/bugs?severity=critical").json()) == 1
        assert len(client.get("/api/bugs?severity=low").json())      == 2

    def test_filter_by_status_and_severity_combined(self, client):
        create(client, severity="high")    # open + high
        create(client, severity="low")     # open + low
        assert len(client.get("/api/bugs?status=open&severity=high").json()) == 1


# ─── Status machine ───────────────────────────────────────────────────────────

class TestStatusMachine:

    def test_new_bug_starts_as_open(self, client):
        assert create(client).json()["status"] == "open"

    def test_open_to_in_progress(self, client):
        bug_id = create(client).json()["id"]
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "in_progress"})
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"

    def test_open_to_closed(self, client):
        bug_id = create(client).json()["id"]
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "closed"})
        assert res.status_code == 200
        assert res.json()["status"] == "closed"

    def test_in_progress_to_closed(self, client):
        bug_id = create(client).json()["id"]
        client.patch(f"/api/bugs/{bug_id}", json={"status": "in_progress"})
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "closed"})
        assert res.status_code == 200
        assert res.json()["status"] == "closed"

    def test_closed_bug_can_be_reopened(self, client):
        bug_id = create(client).json()["id"]
        client.patch(f"/api/bugs/{bug_id}", json={"status": "closed"})
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "open"})
        assert res.status_code == 200
        assert res.json()["status"] == "open"

    def test_invalid_transition_returns_422(self, client):
        """A closed bug cannot jump directly to in_progress."""
        bug_id = create(client).json()["id"]
        client.patch(f"/api/bugs/{bug_id}", json={"status": "closed"})
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "in_progress"})
        assert res.status_code == 422

    def test_same_status_is_invalid_transition(self, client):
        """Setting the same status should also be rejected."""
        bug_id = create(client).json()["id"]
        res = client.patch(f"/api/bugs/{bug_id}", json={"status": "open"})
        assert res.status_code == 422


# ─── Stats ────────────────────────────────────────────────────────────────────

class TestStats:

    def test_stats_all_zero_when_empty(self, client):
        stats = client.get("/api/stats").json()
        assert stats == {"open": 0, "in_progress": 0, "closed": 0}

    def test_stats_reflect_created_bugs(self, client):
        create(client)
        create(client)
        assert client.get("/api/stats").json()["open"] == 2

    def test_stats_update_after_status_change(self, client):
        bug_id = create(client).json()["id"]
        client.patch(f"/api/bugs/{bug_id}", json={"status": "closed"})
        stats = client.get("/api/stats").json()
        assert stats["open"]   == 0
        assert stats["closed"] == 1
