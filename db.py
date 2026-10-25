"""
db.py  (owner: Data + pitch person)

save_score(...)       -> store a finished run
get_leaderboard(...)  -> today's best runs (fewest prompts first)
has_played_today(...) -> did this device already save a score today?

Uses MongoDB if MONGODB_URI is set in .env, otherwise falls back to an
in-memory list so the app works on day one with zero setup.
If MongoDB can't be reached (bad Wi-Fi at the demo), scores fall back to
memory instead of crashing the server.
"""
import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from pymongo.errors import PyMongoError

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

_memory_scores: list[dict] = []   # fallback storage (resets when server restarts)
_collection = None

if MONGODB_URI:
    from pymongo import MongoClient

    try:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _collection = _client["promptgame"]["scores"]
    except PyMongoError as e:
        print(f"[db] couldn't connect to MongoDB, using in-memory scores: {e}")


def save_score(name: str, task_id: int, prompts: int, seconds: float, device_id: str = "") -> dict:
    doc = {
        "name": name[:20] or "anon",
        "device_id": device_id,
        "task_id": task_id,
        "prompts": prompts,
        "seconds": round(seconds, 1),
        "day": date.today().isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _collection is not None:
        try:
            _collection.insert_one(dict(doc))
            return doc
        except PyMongoError as e:
            print(f"[db] save failed, keeping score in memory: {e}")
    _memory_scores.append(doc)
    return doc


def has_played_today(device_id: str) -> bool:
    today = date.today().isoformat()
    if _collection is not None:
        try:
            return _collection.find_one({"device_id": device_id, "day": today}) is not None
        except PyMongoError as e:
            print(f"[db] played-today check failed, checking in-memory scores: {e}")
    return any(s["device_id"] == device_id and s["day"] == today for s in _memory_scores)


def get_leaderboard(limit: int = 10) -> list[dict]:
    today = date.today().isoformat()
    # device_id stays private: it's the lock that stops replays, so it's never sent out
    if _collection is not None:
        try:
            cursor = (
                _collection.find({"day": today}, {"_id": 0, "device_id": 0})
                .sort([("prompts", 1), ("seconds", 1)])
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError as e:
            print(f"[db] leaderboard read failed, showing in-memory scores: {e}")
    todays = [s for s in _memory_scores if s["day"] == today]
    todays.sort(key=lambda s: (s["prompts"], s["seconds"]))
    return [{k: v for k, v in s.items() if k != "device_id"} for s in todays[:limit]]
