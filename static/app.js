// ─── Constants ────────────────────────────────────────────────────────────────

const SEVERITY_STYLES = {
  critical: "danger",
  high:     "warning",
  medium:   "secondary",
  low:      "light text-dark border",
};

const STATUS_STYLES = {
  open:        "primary",
  in_progress: "warning text-dark",
  closed:      "success",
};

const STATUS_LABELS = {
  open:        "Open",
  in_progress: "In Progress",
  closed:      "Closed",
};

// What transitions are allowed from each status
const VALID_TRANSITIONS = {
  open:        ["in_progress", "closed"],
  in_progress: ["open", "closed"],
  closed:      ["open"],
};

// ─── State ────────────────────────────────────────────────────────────────────

let allBugs = [];
let bugModal = null;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  bugModal = new bootstrap.Modal(document.getElementById("bugModal"));

  document.getElementById("btn-new-bug").addEventListener("click", openCreateModal);
  document.getElementById("btn-save-bug").addEventListener("click", saveBug);
  document.getElementById("filter-status").addEventListener("change", renderTable);
  document.getElementById("filter-severity").addEventListener("change", renderTable);

  loadBugs();
});

// ─── API calls ────────────────────────────────────────────────────────────────

async function loadBugs() {
  const res = await fetch("/api/bugs");
  allBugs = await res.json();
  renderTable();
  loadStats();
}

async function loadStats() {
  const res = await fetch("/api/stats");
  const stats = await res.json();
  document.getElementById("stat-open").textContent        = stats.open        ?? 0;
  document.getElementById("stat-in-progress").textContent = stats.in_progress ?? 0;
  document.getElementById("stat-closed").textContent      = stats.closed      ?? 0;
}

async function saveBug() {
  const id    = document.getElementById("edit-id").value;
  const title = document.getElementById("field-title").value.trim();
  if (!title) {
    document.getElementById("field-title").classList.add("is-invalid");
    return;
  }

  const body = {
    title,
    description:        document.getElementById("field-description").value,
    steps_to_reproduce: document.getElementById("field-steps").value,
    expected_result:    document.getElementById("field-expected").value,
    actual_result:      document.getElementById("field-actual").value,
    severity:           document.getElementById("field-severity").value,
    reporter:           document.getElementById("field-reporter").value,
  };

  const url    = id ? `/api/bugs/${id}` : "/api/bugs";
  const method = id ? "PATCH" : "POST";

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    bugModal.hide();
    loadBugs();
  }
}

async function changeStatus(bugId, newStatus) {
  await fetch(`/api/bugs/${bugId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newStatus }),
  });
  loadBugs();
  bugModal.hide();
}

async function deleteBug(id) {
  if (!confirm("Delete this bug permanently?")) return;
  await fetch(`/api/bugs/${id}`, { method: "DELETE" });
  bugModal.hide();
  loadBugs();
}

// ─── Modal helpers ────────────────────────────────────────────────────────────

function openCreateModal() {
  document.getElementById("modal-title").textContent = "New Bug";
  document.getElementById("edit-id").value           = "";
  document.getElementById("field-title").value       = "";
  document.getElementById("field-title").classList.remove("is-invalid");
  document.getElementById("field-description").value = "";
  document.getElementById("field-steps").value       = "";
  document.getElementById("field-expected").value    = "";
  document.getElementById("field-actual").value      = "";
  document.getElementById("field-severity").value    = "medium";
  document.getElementById("field-reporter").value    = "";
  document.getElementById("status-section").classList.add("d-none");
  document.getElementById("btn-delete-bug").classList.add("d-none");
  bugModal.show();
}

function openEditModal(bug) {
  document.getElementById("modal-title").textContent    = `Bug #${bug.id}`;
  document.getElementById("edit-id").value              = bug.id;
  document.getElementById("field-title").value          = bug.title;
  document.getElementById("field-title").classList.remove("is-invalid");
  document.getElementById("field-description").value   = bug.description || "";
  document.getElementById("field-steps").value         = bug.steps_to_reproduce || "";
  document.getElementById("field-expected").value      = bug.expected_result || "";
  document.getElementById("field-actual").value        = bug.actual_result || "";
  document.getElementById("field-severity").value      = bug.severity;
  document.getElementById("field-reporter").value      = bug.reporter || "";

  // Status transition buttons
  document.getElementById("status-section").classList.remove("d-none");
  const btnContainer = document.getElementById("status-buttons");
  btnContainer.innerHTML = `<span class="me-2">Current: ${statusBadge(bug.status)}</span>`;
  VALID_TRANSITIONS[bug.status].forEach((next) => {
    const btn = document.createElement("button");
    btn.className = "btn btn-sm btn-outline-secondary";
    btn.textContent = `→ ${STATUS_LABELS[next]}`;
    btn.addEventListener("click", () => changeStatus(bug.id, next));
    btnContainer.appendChild(btn);
  });

  // Delete button
  const delBtn = document.getElementById("btn-delete-bug");
  delBtn.classList.remove("d-none");
  delBtn.onclick = () => deleteBug(bug.id);

  bugModal.show();
}

// ─── Render ───────────────────────────────────────────────────────────────────

function renderTable() {
  const statusFilter   = document.getElementById("filter-status").value;
  const severityFilter = document.getElementById("filter-severity").value;
  const tbody          = document.getElementById("bugs-body");
  const emptyRow       = document.getElementById("empty-row");

  const filtered = allBugs.filter((b) => {
    if (statusFilter   && b.status   !== statusFilter)   return false;
    if (severityFilter && b.severity !== severityFilter) return false;
    return true;
  });

  document.getElementById("bug-count").textContent =
    `${filtered.length} bug${filtered.length !== 1 ? "s" : ""}`;

  tbody.querySelectorAll("tr:not(#empty-row)").forEach((r) => r.remove());

  if (filtered.length === 0) {
    emptyRow.classList.remove("d-none");
    return;
  }
  emptyRow.classList.add("d-none");

  filtered.forEach((bug) => {
    const tr = document.createElement("tr");
    tr.dataset.id = bug.id;
    tr.innerHTML = `
      <td class="text-muted small">#${bug.id}</td>
      <td class="fw-semibold">${escapeHtml(bug.title)}</td>
      <td class="text-muted small">${escapeHtml(bug.reporter || "—")}</td>
      <td>${severityBadge(bug.severity)}</td>
      <td>${statusBadge(bug.status)}</td>
      <td class="text-muted small">${bug.created_at?.slice(0, 10) ?? "—"}</td>
      <td><i class="bi bi-chevron-right text-muted"></i></td>
    `;
    tr.addEventListener("click", () => openEditModal(bug));
    tbody.appendChild(tr);
  });
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function severityBadge(severity) {
  const style = SEVERITY_STYLES[severity] ?? "secondary";
  return `<span class="badge bg-${style}">${severity.toUpperCase()}</span>`;
}

function statusBadge(status) {
  const style = STATUS_STYLES[status] ?? "secondary";
  const label = STATUS_LABELS[status] ?? status;
  return `<span class="badge bg-${style}">${label}</span>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
