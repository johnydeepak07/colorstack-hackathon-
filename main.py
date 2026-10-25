"""
main.py  (owner: Backend/AI person)

Run with:   uvicorn main:app --reload
API docs:   http://127.0.0.1:8000/docs   (test endpoints here, no frontend needed)
Game:       http://127.0.0.1:8000/

THE CONTRACT (don't change these JSON shapes without telling the team):

  GET  /api/task          ?device_id=... (optional)
                          -> {id, title, details, played_today}
  POST /api/prompt        body: {session_id, prompt}
                          -> {reply, passed, prompt_count, seconds}   (seconds is null until passed)
  POST /api/score         body: {session_id, name, device_id (optional)}
                          -> {saved: true, prompts, seconds}
  GET  /api/leaderboard   -> [{name, prompts, seconds, ...}, ...]
"""
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db
import llm
from tasks import TASKS_BY_ID, get_todays_task, is_passing, public_view

app = FastAPI(title="Prompt Game")

MAX_PROMPTS_PER_SESSION = 30   # caps Groq usage per player
MAX_HISTORY_SENT = 21          # odd so the trimmed history still starts with a user message
MAX_SESSIONS = 5000            # oldest sessions are dropped past this
RATE_LIMIT = 15                # prompts per IP address...
RATE_WINDOW = 60               # ...per this many seconds (stops scripts from draining Groq quota)
ALLOW_REPLAY = os.getenv("ALLOW_REPLAY") == "1"   # set ALLOW_REPLAY=1 in .env to turn off once-a-day (demo laptop)

# In-memory per-player state. Fine for a hackathon (resets on server restart).
# sessions[session_id] = {"history": [...], "prompts": int, "start": float, "passed": bool, "task_id": int}
sessions: dict[str, dict] = {}
_recent_prompts: dict[str, deque] = defaultdict(deque)   # ip -> timestamps of recent prompts


class PromptBody(BaseModel):
    session_id: str = Field(max_length=100)
    prompt: str


class ScoreBody(BaseModel):
    session_id: str = Field(max_length=100)
    name: str = Field(max_length=100)
    device_id: str = Field(default="", max_length=100)   # optional, so older frontends still work


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))   # dicts keep insertion order, so this is the oldest
        sessions[session_id] = {
            "history": [],
            "prompts": 0,
            "start": time.time(),
            "passed": False,
            # Locked in so a game in progress at midnight keeps its task
            "task_id": get_todays_task()["id"],
        }
    return sessions[session_id]


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    stamps = _recent_prompts[ip]
    while stamps and now - stamps[0] > RATE_WINDOW:
        stamps.popleft()
    if len(stamps) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Slow down - too many prompts. Wait a minute and try again.")
    stamps.append(now)


def _already_played(device_id: str) -> bool:
    return bool(device_id) and not ALLOW_REPLAY and db.has_played_today(device_id)


@app.get("/api/task")
def get_task(device_id: str = Query(default="", max_length=100)):
    task = public_view(get_todays_task())
    task["played_today"] = _already_played(device_id)
    return task


@app.post("/api/prompt")
def send_prompt(body: PromptBody, request: Request):
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt can't be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 chars)")

    s = _get_session(body.session_id)
    if s["passed"]:
        raise HTTPException(status_code=400, detail="Already solved - submit your score!")
    if s["prompts"] >= MAX_PROMPTS_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail=f"Out of prompts ({MAX_PROMPTS_PER_SESSION} max). Refresh the page to start over.",
        )
    _check_rate_limit(request.client.host if request.client else "unknown")

    user_msg = {"role": "user", "content": prompt}
    try:
        reply = llm.ask((s["history"] + [user_msg])[-MAX_HISTORY_SENT:])
    except llm.LLMError as e:
        # The prompt isn't counted or saved, so a failed call doesn't cost the player
        raise HTTPException(status_code=503, detail=str(e))

    s["history"].append(user_msg)
    s["history"].append({"role": "assistant", "content": reply})
    s["prompts"] += 1

    task = TASKS_BY_ID[s["task_id"]]
    user_prompts = [m["content"] for m in s["history"] if m["role"] == "user"]
    passed = is_passing(task, reply, user_prompts)
    s["passed"] = passed
    if passed:
        # Clock stops at the solve, not when the score is submitted (typing a name is free).
        # The page shows this same number, so the win card and leaderboard always match.
        s["seconds"] = round(time.time() - s["start"], 1)

    return {"reply": reply, "passed": passed, "prompt_count": s["prompts"], "seconds": s.get("seconds")}


@app.post("/api/score")
def submit_score(body: ScoreBody):
    s = sessions.get(body.session_id)
    if not s or not s["passed"]:
        raise HTTPException(status_code=400, detail="Solve the task first!")
    if s.get("score_saved"):
        raise HTTPException(status_code=400, detail="Score already saved!")
    if _already_played(body.device_id):
        raise HTTPException(status_code=400, detail="You already played today - come back tomorrow!")
    db.save_score(body.name.strip(), s["task_id"], s["prompts"], s["seconds"], body.device_id)
    s["score_saved"] = True
    return {"saved": True, "prompts": s["prompts"], "seconds": s["seconds"]}


@app.get("/api/leaderboard")
def leaderboard():
    return db.get_leaderboard()


# ---- frontend (Frontend person owns the static/ folder) ----
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
