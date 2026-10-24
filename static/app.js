// Frontend person: this file talks to the backend using the contract in main.py.
// It works with the real backend OR with the stub replies, same JSON shape.

// One id per browser tab so the backend can track this player's attempt.
const sessionId = crypto.randomUUID();

const els = {
  title: document.getElementById("task-title"),
  details: document.getElementById("task-details"),
  count: document.getElementById("count"),
  messages: document.getElementById("messages"),
  promptForm: document.getElementById("prompt-form"),
  promptInput: document.getElementById("prompt-input"),
  sendBtn: document.getElementById("send-btn"),
  winCard: document.getElementById("win-card"),
  winText: document.getElementById("win-text"),
  scoreForm: document.getElementById("score-form"),
  nameInput: document.getElementById("name-input"),
  leaderboard: document.getElementById("leaderboard"),
};

function addMessage(text, kind) {
  const div = document.createElement("div");
  div.className = "msg " + kind;
  div.textContent = text;           // textContent (not innerHTML) so AI output can't inject HTML
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function loadTask() {
  const res = await fetch("/api/task");
  const task = await res.json();
  els.title.textContent = task.title;
  els.details.textContent = task.details;
}

async function loadLeaderboard() {
  const res = await fetch("/api/leaderboard");
  const rows = await res.json();
  els.leaderboard.innerHTML = "";
  if (rows.length === 0) {
    els.leaderboard.innerHTML = '<li class="muted">No scores yet</li>';
    return;
  }
  rows.forEach((r) => {
    const li = document.createElement("li");
    li.textContent = `${r.name} - ${r.prompts} prompt${r.prompts === 1 ? "" : "s"} (${r.seconds}s)`;
    els.leaderboard.appendChild(li);
  });
}

els.promptForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = els.promptInput.value.trim();
  if (!prompt) return;

  addMessage(prompt, "user");
  els.promptInput.value = "";
  els.sendBtn.disabled = true;

  try {
    const res = await fetch("/api/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, prompt }),
    });
    const data = await res.json();
    if (!res.ok) {
      addMessage(data.detail || "Something went wrong", "system");
      return;
    }
    els.count.textContent = data.prompt_count;
    addMessage(data.reply, data.passed ? "ai pass" : "ai");

    if (data.passed) {
      addMessage("Task complete!", "system");
      els.winText.textContent = `Solved in ${data.prompt_count} prompt${data.prompt_count === 1 ? "" : "s"}.`;
      els.winCard.classList.remove("hidden");
      els.promptForm.classList.add("hidden");
    }
  } catch (err) {
    addMessage("Network error - is the server running?", "system");
  } finally {
    els.sendBtn.disabled = false;
    els.promptInput.focus();
  }
});

els.scoreForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const res = await fetch("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, name: els.nameInput.value }),
  });
  if (res.ok) {
    els.scoreForm.classList.add("hidden");
    els.winText.textContent += " Score saved!";
    loadLeaderboard();
  }
});

loadTask();
loadLeaderboard();
