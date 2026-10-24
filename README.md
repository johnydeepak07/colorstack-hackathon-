# Prompt Daily

A daily prompt-engineering game. Each day has one task. Get the AI to complete it in as few prompts as possible.

## Run it (first 5 minutes)
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 (game) and http://127.0.0.1:8000/docs (API tester).

It runs with NO keys: AI replies are fake and scores live in memory.
Add `ANTHROPIC_API_KEY` to `.env` for the real AI, and `MONGODB_URI` for real storage.

## Who owns what
| Person | Files | First job |
|---|---|---|
| Frontend | `static/` | Make it look great; keep element IDs used in `app.js` |
| Backend/AI | `main.py`, `llm.py`, `tasks.py` (checkers) | Plug in the real LLM, tune the checkers |
| Data + pitch | `db.py`, `tasks.py` (task list) | Connect MongoDB, write 5-7 good tasks, build the demo |

## The contract (don't change JSON shapes without telling the team)
```
GET  /api/task          -> {id, title, details}
POST /api/prompt        {session_id, prompt} -> {reply, passed, prompt_count}
POST /api/score         {session_id, name}   -> {saved, prompts, seconds}
GET  /api/leaderboard   -> [{name, prompts, seconds, ...}]
```

## Git workflow
- `main` always works. Each person uses their own branch: `git checkout -b frontend`.
- Commit small, merge into `main` often, and `git pull` before you start working.

## Ideas if you finish early
1. Streaks and share button ("I solved it in 2 prompts")
2. Hint system that costs extra points
3. Difficulty tiers
4. Harder tasks that need prompt tricks (system-prompt style constraints)
