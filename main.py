from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    create_bug, delete_bug, get_bug, get_bugs, get_stats, init_db, update_bug,
)

app = FastAPI(title="Bug Tracker")

# Valid status transitions: defines the bug lifecycle
VALID_TRANSITIONS = {
    "open":        {"in_progress", "closed"},
    "in_progress": {"open", "closed"},
    "closed":      {"open"},
}

VALID_STATUSES   = {"open", "in_progress", "closed"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


@app.on_event("startup")
async def startup():
    init_db()


# ─── Pydantic models ──────────────────────────────────────────────────────────

class BugCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = ""
    steps_to_reproduce: Optional[str] = ""
    expected_result: Optional[str] = ""
    actual_result: Optional[str] = ""
    severity: Optional[str] = "medium"
    reporter: Optional[str] = ""


class BugUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    reporter: Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/bugs")
def list_bugs(status: Optional[str] = None, severity: Optional[str] = None):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status}")
    if severity and severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"Invalid severity: {severity}")
    return get_bugs(status=status, severity=severity)


@app.post("/api/bugs", status_code=201)
def create(body: BugCreate):
    if body.severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"Invalid severity: {body.severity}")
    return create_bug(
        title=body.title,
        description=body.description or "",
        steps_to_reproduce=body.steps_to_reproduce or "",
        expected_result=body.expected_result or "",
        actual_result=body.actual_result or "",
        severity=body.severity,
        reporter=body.reporter or "",
    )


@app.get("/api/bugs/{bug_id}")
def get_one(bug_id: int):
    bug = get_bug(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found.")
    return bug


@app.patch("/api/bugs/{bug_id}")
def update(bug_id: int, body: BugUpdate):
    bug = get_bug(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found.")

    fields = body.model_dump(exclude_none=True)

    # Validate and enforce the status machine
    if "status" in fields:
        new_status = fields["status"]
        if new_status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Invalid status: {new_status}")
        current = bug["status"]
        if new_status not in VALID_TRANSITIONS[current]:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot transition from '{current}' to '{new_status}'.",
            )

    if "severity" in fields and fields["severity"] not in VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"Invalid severity: {fields['severity']}")

    return update_bug(bug_id, fields)


@app.delete("/api/bugs/{bug_id}")
def delete(bug_id: int):
    if not delete_bug(bug_id):
        raise HTTPException(status_code=404, detail="Bug not found.")
    return {"ok": True}


@app.get("/api/stats")
def stats():
    return get_stats()


app.mount("/", StaticFiles(directory="static", html=True), name="static")
