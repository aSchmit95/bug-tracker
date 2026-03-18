# Bug Tracker

A minimal CRUD app to log and manage bugs, with a full test suite covering the
complete bug lifecycle, status machine transitions, and edge cases.

**Stack:** FastAPI · SQLite · Vanilla JS · Bootstrap 5

**Tests:** 27 integration tests (pytest) · 8 E2E tests (Playwright)

---

## Features

- Create bugs with title, description, steps to reproduce, expected/actual result, severity, and reporter
- Status lifecycle: `open` → `in_progress` → `closed` (with reopen support)
- Invalid transitions are rejected (e.g. `closed` → `in_progress`)
- Filter bugs by status and/or severity
- Live stats counter per status
- Delete bugs with confirmation

---

## QA Focus

- **Status machine testing** — every valid and invalid transition is explicitly tested
- **Integration tests** hit a real (isolated temp) SQLite database — no mocked DB
- **E2E tests** cover the full UI flow: create, edit, transition, delete, filter
- Validated that invalid status transitions return `422` at the API level and are blocked in the UI

---

## Running the App

```bash
uv run uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## Running the Tests

```bash
# Integration tests
uv run pytest tests/test_api.py -v

# E2E tests (requires Playwright browsers)
uv run playwright install chromium
uv run pytest tests/test_e2e.py -v
```
