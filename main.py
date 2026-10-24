"""
main.py  (owner: Backend/AI person)

Run with:   uvicorn main:app --reload
API docs:   http://127.0.0.1:8000/docs   (test endpoints here, no frontend needed)
Game:       http://127.0.0.1:8000/

THE CONTRACT (don't change these JSON shapes without telling the team):

  GET  /api/task          -> {id, title, details}
  POST /api/prompt        body: {session_id, prompt}
                          -> {reply, passed, prompt_count}
  POST /api/score         body: {session_id, name}
                          -> {saved: true, prompts, seconds}
  GET  /api/leaderboard   -> [{name, prompts, seconds, ...}, ...]
"""
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import llm
from tasks import get_todays_task, is_passing, public_view

app = FastAPI(title="Prompt Game")

# In-memory per-player state. Fine for a hackathon (resets on server restart).
# sessions[session_id] = {"history": [...], "prompts": int, "start": float, "passed": bool}
sessions: dict[str, dict] = {}


class PromptBody(BaseModel):
    session_id: str
    prompt: str


class ScoreBody(BaseModel):
    session_id: str
    name: str


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "prompts": 0,
            "start": time.time(),
            "passed": False,
        }
    return sessions[session_id]


@app.get("/api/task")
def get_task():
    return public_view(get_todays_task())


@app.post("/api/prompt")
def send_prompt(body: PromptBody):
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt can't be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 chars)")

    s = _get_session(body.session_id)
    if s["passed"]:
        raise HTTPException(status_code=400, detail="Already solved - submit your score!")

    s["history"].append({"role": "user", "content": prompt})
    s["prompts"] += 1

    reply = llm.ask(s["history"])
    s["history"].append({"role": "assistant", "content": reply})

    task = get_todays_task()
    user_prompts = [m["content"] for m in s["history"] if m["role"] == "user"]
    passed = is_passing(task, reply, user_prompts)
    s["passed"] = passed

    return {"reply": reply, "passed": passed, "prompt_count": s["prompts"]}


@app.post("/api/score")
def submit_score(body: ScoreBody):
    s = sessions.get(body.session_id)
    if not s or not s["passed"]:
        raise HTTPException(status_code=400, detail="Solve the task first!")
    seconds = time.time() - s["start"]
    task = get_todays_task()
    db.save_score(body.name.strip(), task["id"], s["prompts"], seconds)
    return {"saved": True, "prompts": s["prompts"], "seconds": round(seconds, 1)}


@app.get("/api/leaderboard")
def leaderboard():
    return db.get_leaderboard()


# ---- frontend (Frontend person owns the static/ folder) ----
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
