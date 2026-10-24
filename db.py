"""
db.py  (owner: Data + pitch person)

save_score(...)       -> store a finished run
get_leaderboard(...)  -> today's best runs (fewest prompts first)

Uses MongoDB if MONGODB_URI is set in .env, otherwise falls back to an
in-memory list so the app works on day one with zero setup.
"""
import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

_memory_scores: list[dict] = []   # fallback storage (resets when server restarts)
_collection = None

if MONGODB_URI:
    from pymongo import MongoClient

    _client = MongoClient(MONGODB_URI)
    _collection = _client["promptgame"]["scores"]


def save_score(name: str, task_id: int, prompts: int, seconds: float) -> dict:
    doc = {
        "name": name[:20] or "anon",
        "task_id": task_id,
        "prompts": prompts,
        "seconds": round(seconds, 1),
        "day": date.today().isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _collection is not None:
        _collection.insert_one(dict(doc))
    else:
        _memory_scores.append(doc)
    return doc


def get_leaderboard(limit: int = 10) -> list[dict]:
    today = date.today().isoformat()
    if _collection is not None:
        cursor = (
            _collection.find({"day": today}, {"_id": 0})
            .sort([("prompts", 1), ("seconds", 1)])
            .limit(limit)
        )
        return list(cursor)
    todays = [s for s in _memory_scores if s["day"] == today]
    todays.sort(key=lambda s: (s["prompts"], s["seconds"]))
    return todays[:limit]
