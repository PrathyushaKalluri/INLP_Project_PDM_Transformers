/**
 * STEP 6 — Task Board Frontend Logic
 *
 * Loads tasks from the /tasks endpoint and renders them as cards.
 * Each card has a "Show Evidence" button that fetches transcript
 * evidence from /evidence/{task_id} and displays it inline.
 */

(function () {
  "use strict";

  const board = document.getElementById("board");

  // ---- Fetch & render tasks ----

  async function loadTasks() {
    try {
      const res = await fetch("/tasks");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const tasks = await res.json();

      board.innerHTML = "";

      if (tasks.length === 0) {
        board.innerHTML = '<div class="status-msg">No tasks found.</div>';
        return;
      }

      tasks.forEach((task) => board.appendChild(createCard(task)));
    } catch (err) {
      board.innerHTML =
        '<div class="status-msg">Failed to load tasks. Is the server running?</div>';
      console.error("loadTasks error:", err);
    }
  }

  // ---- Build a single task card ----

  function createCard(task) {
    const card = document.createElement("div");
    card.className = "task-card";
    card.dataset.taskId = task.task_id;

    // Title
    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;
    card.appendChild(title);

    // Meta badges
    const meta = document.createElement("div");
    meta.className = "task-meta";

    // Assignee badge
    const assignee = document.createElement("span");
    assignee.className = "badge badge-assignee";
    assignee.innerHTML =
      '<span class="badge-icon">👤</span> Assignee: ' + escapeHtml(task.assignee);
    meta.appendChild(assignee);

    // Deadline badge (only when present)
    if (task.deadline) {
      const deadline = document.createElement("span");
      deadline.className = "badge badge-deadline";
      deadline.innerHTML =
        '<span class="badge-icon">📅</span> Deadline: ' + escapeHtml(task.deadline);
      meta.appendChild(deadline);
    }

    card.appendChild(meta);

    // Evidence toggle button
    const btn = document.createElement("button");
    btn.className = "evidence-btn";
    btn.innerHTML = '<span class="arrow">▶</span> Show Evidence';
    card.appendChild(btn);

    // Evidence panel (hidden by default)
    const panel = document.createElement("div");
    panel.className = "evidence-panel";
    card.appendChild(panel);

    // Click handler
    btn.addEventListener("click", () => toggleEvidence(task.task_id, btn, panel));

    return card;
  }

  // ---- Toggle evidence panel ----

  async function toggleEvidence(taskId, btn, panel) {
    // If already open → close
    if (panel.classList.contains("open")) {
      panel.classList.remove("open");
      btn.classList.remove("open");
      btn.innerHTML = '<span class="arrow">▶</span> Show Evidence';
      return;
    }

    // Fetch evidence if panel is empty
    if (panel.children.length === 0) {
      panel.innerHTML = '<div class="status-msg">Loading…</div>';
      panel.classList.add("open");

      try {
        const res = await fetch("/evidence/" + taskId);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        panel.innerHTML = "";

        if (data.evidence.length === 0) {
          panel.innerHTML = '<div class="status-msg">No evidence found.</div>';
        } else {
          data.evidence.forEach((e) => {
            const item = document.createElement("div");
            item.className = "evidence-item";

            const speaker = document.createElement("div");
            speaker.className = "evidence-speaker";
            speaker.textContent = "Speaker: " + e.speaker;
            item.appendChild(speaker);

            const text = document.createElement("div");
            text.className = "evidence-text";
            text.textContent = '"' + e.text + '"';
            item.appendChild(text);

            const sid = document.createElement("div");
            sid.className = "evidence-sid";
            sid.textContent = "Sentence #" + e.sentence_id;
            item.appendChild(sid);

            panel.appendChild(item);
          });
        }
      } catch (err) {
        panel.innerHTML = '<div class="status-msg">Failed to load evidence.</div>';
        console.error("loadEvidence error:", err);
      }
    }

    // Open the panel
    panel.classList.add("open");
    btn.classList.add("open");
    btn.innerHTML = '<span class="arrow">▶</span> Hide Evidence';
  }

  // ---- Helpers ----

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---- Kick off ----

  document.addEventListener("DOMContentLoaded", loadTasks);
})();
