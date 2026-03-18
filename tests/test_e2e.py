"""
End-to-end tests for the Bug Tracker UI.
Runs against a real local server (live_server fixture in conftest.py).
"""

import httpx
import pytest
from playwright.sync_api import Page, expect

from conftest import SAMPLE_BUG


@pytest.fixture(autouse=True)
def clean_bugs(live_server):
    """Delete all bugs after each test so the next one starts fresh."""
    yield
    for bug in httpx.get(f"{live_server}/api/bugs").json():
        httpx.delete(f"{live_server}/api/bugs/{bug['id']}")


def create_bug_via_api(live_server, **overrides):
    res = httpx.post(f"{live_server}/api/bugs", json={**SAMPLE_BUG, **overrides})
    return res.json()


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_page_loads(page: Page, live_server: str):
    page.goto(live_server)
    expect(page).to_have_title("Bug Tracker")
    expect(page.locator("#btn-new-bug")).to_be_visible()
    expect(page.locator("#empty-row")).to_be_visible()


def test_stats_show_zeros_initially(page: Page, live_server: str):
    page.goto(live_server)
    expect(page.locator("#stat-open")).to_have_text("0")
    expect(page.locator("#stat-in-progress")).to_have_text("0")
    expect(page.locator("#stat-closed")).to_have_text("0")


def test_create_bug_appears_in_table(page: Page, live_server: str):
    page.goto(live_server)

    page.locator("#btn-new-bug").click()
    page.locator("#field-title").fill(SAMPLE_BUG["title"])
    page.locator("#field-severity").select_option("high")
    page.locator("#field-reporter").fill(SAMPLE_BUG["reporter"])
    page.locator("#btn-save-bug").click()

    expect(page.locator("#empty-row")).to_be_hidden(timeout=5_000)
    expect(page.locator("#bugs-body")).to_contain_text(SAMPLE_BUG["title"])


def test_stats_update_after_creating_bug(page: Page, live_server: str):
    create_bug_via_api(live_server)
    page.goto(live_server)
    expect(page.locator("#stat-open")).to_have_text("1")


def test_click_bug_opens_edit_modal(page: Page, live_server: str):
    bug = create_bug_via_api(live_server)
    page.goto(live_server)

    page.locator(f"tr[data-id='{bug['id']}']").click()
    expect(page.locator("#bugModal")).to_be_visible()
    expect(page.locator("#field-title")).to_have_value(bug["title"])


def test_status_transition_via_ui(page: Page, live_server: str):
    bug = create_bug_via_api(live_server)
    page.goto(live_server)

    # Open the edit modal and click "→ In Progress"
    page.locator(f"tr[data-id='{bug['id']}']").click()
    expect(page.locator("#bugModal")).to_be_visible()
    page.get_by_text("→ In Progress").click()

    # Status badge in the table should update
    expect(page.locator(f"tr[data-id='{bug['id']}']")).to_contain_text(
        "In Progress", timeout=5_000
    )
    # Stats should reflect the change
    expect(page.locator("#stat-in-progress")).to_have_text("1")
    expect(page.locator("#stat-open")).to_have_text("0")


def test_delete_bug_from_ui(page: Page, live_server: str):
    bug = create_bug_via_api(live_server)
    page.goto(live_server)

    page.locator(f"tr[data-id='{bug['id']}']").click()
    expect(page.locator("#bugModal")).to_be_visible()

    page.on("dialog", lambda d: d.accept())
    page.locator("#btn-delete-bug").click()

    expect(page.locator("#empty-row")).to_be_visible(timeout=5_000)


def test_filter_by_status(page: Page, live_server: str):
    open_bug   = create_bug_via_api(live_server, title="Open bug")
    closed_bug = create_bug_via_api(live_server, title="Closed bug")
    httpx.patch(
        f"{live_server}/api/bugs/{closed_bug['id']}",
        json={"status": "closed"},
    )

    page.goto(live_server)
    expect(page.locator("#bugs-body tr:not(#empty-row)")).to_have_count(2)

    page.select_option("#filter-status", "open")
    expect(page.locator("#bugs-body tr:not(#empty-row)")).to_have_count(1)
    expect(page.locator("#bugs-body")).to_contain_text("Open bug")

    page.select_option("#filter-status", "closed")
    expect(page.locator("#bugs-body tr:not(#empty-row)")).to_have_count(1)
    expect(page.locator("#bugs-body")).to_contain_text("Closed bug")
