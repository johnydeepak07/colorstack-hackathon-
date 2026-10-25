// Talks to the backend using the contract in main.py.
// Works with the real backend OR the stub replies, same JSON shape.

// One id per browser tab so the backend can track this player's attempt.
const sessionId = crypto.randomUUID();

const els = {
  title: document.getElementById("task-title"),
  details: document.getElementById("task-details"),
  count: document.getElementById("count"),
  timer: document.getElementById("timer"),
  messages: document.getElementById("messages"),
  promptForm: document.getElementById("prompt-form"),
  promptInput: document.getElementById("prompt-input"),
  sendBtn: document.getElementById("send-btn"),
  winCard: document.getElementById("win-card"),
  winText: document.getElementById("win-text"),
  winTime: document.getElementById("win-time"),
  scoreForm: document.getElementById("score-form"),
  nameInput: document.getElementById("name-input"),
  shareBtn: document.getElementById("share-btn"),
  leaderboard: document.getElementById("leaderboard"),
};

let startedAt = null, timerHandle = null;

const plural = (n) => `prompt${n === 1 ? "" : "s"}`;
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function startTimer() {
  if (startedAt) return;
  startedAt = Date.now();
  timerHandle = setInterval(() => {
    els.timer.textContent = fmtTime((Date.now() - startedAt) / 1000);
  }, 500);
}

function addMessage(text, kind) {
  els.messages.querySelector(".empty")?.remove();
  const div = document.createElement("div");
  div.className = "msg " + kind;
  div.textContent = text;           // textContent (not innerHTML) so AI output can't inject HTML
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

async function loadTask() {
  try {
    const res = await fetch("/api/task");
    const task = await res.json();
    els.title.textContent = task.title;
    els.details.textContent = task.details;
  } catch (err) {
    els.title.textContent = "Couldn't load today's task";
    els.details.textContent = "Check that the server is running, then refresh.";
  }
}

async function loadLeaderboard() {
  try {
    const res = await fetch("/api/leaderboard");
    const rows = await res.json();
    els.leaderboard.innerHTML = "";
    if (rows.length === 0) {
      els.leaderboard.innerHTML = '<li class="muted">No scores yet</li>';
      return;
    }
    rows.forEach((r) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.className = "lb-name";
      name.textContent = r.name;
      const stats = document.createElement("span");
      stats.className = "lb-stats";
      stats.textContent = `${r.prompts} ${plural(r.prompts)} · ${fmtTime(r.seconds ?? 0)}`;
      li.append(name, stats);
      els.leaderboard.appendChild(li);
    });
  } catch (err) { /* leaderboard is non-critical */ }
}

els.promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.promptForm.requestSubmit();
  }
});

els.promptForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = els.promptInput.value.trim();
  if (!prompt || els.sendBtn.disabled) return;

  startTimer();
  addMessage(prompt, "user");
  els.promptInput.value = "";
  els.sendBtn.disabled = true;
  const thinking = addMessage("Thinking...", "ai thinking");

  try {
    const res = await fetch("/api/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, prompt }),
    });
    const data = await res.json();
    thinking.remove();
    if (!res.ok) {
      addMessage(data.detail || "Something went wrong", "system");
      return;
    }
    els.count.textContent = data.prompt_count;
    els.count.classList.remove("bump");
    void els.count.offsetWidth;       // restart the animation
    els.count.classList.add("bump");
    addMessage(data.reply, data.passed ? "ai pass" : "ai");

    if (data.passed) {
      clearInterval(timerHandle);
      els.winTime.textContent = `Time: ${fmtTime((Date.now() - startedAt) / 1000)}`;
      addMessage("Task complete!", "system");
      els.winText.textContent = `Solved in ${data.prompt_count} ${plural(data.prompt_count)}.`;
      els.winCard.classList.add("open");
      loadLeaderboard();
      els.promptForm.classList.add("hidden");
      els.nameInput.focus();
    }
  } catch (err) {
    thinking.remove();
    addMessage("Network error - is the server running?", "system");
  } finally {
    els.sendBtn.disabled = false;
    if (!els.promptForm.classList.contains("hidden")) els.promptInput.focus();
  }
});

els.scoreForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter;
  if (btn.disabled) return;
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    const res = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, name: els.nameInput.value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    els.scoreForm.classList.add("hidden");
    els.winText.textContent += " Score saved!";
    els.shareBtn.classList.remove("hidden");
    els.shareBtn.onclick = async () => {
      const text = `I solved today's Promptless in ${data.prompts} ${plural(data.prompts)} (${fmtTime(data.seconds)}). Can you beat it?`;
      try { await navigator.clipboard.writeText(text); els.shareBtn.textContent = "Copied"; }
      catch { els.shareBtn.textContent = text; }
    };
    loadLeaderboard();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Save score";
    addMessage("Couldn't save your score. Try again.", "system");
  }
});

loadTask();
loadLeaderboard();

