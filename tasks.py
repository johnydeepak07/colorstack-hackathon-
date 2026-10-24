"""
tasks.py  (owner: Data + pitch person writes tasks, Backend person writes checkers)

Each task has:
  - id:      unique int
  - title:   short text shown to the player
  - details: optional extra explanation
  - check:   function(reply: str) -> bool   (True = player passed the task)

HOW TO ADD A TASK: write a checker function, then add a dict to TASKS.
Keep checkers simple and deterministic (regex, json.loads, word counts).
"""
import json
import re
from datetime import date


# ---------- checker functions ----------

def check_three_words(reply: str) -> bool:
    words = re.findall(r"[A-Za-z']+", reply)
    return len(words) == 3


def check_json_keys(reply: str) -> bool:
    """Reply must be ONLY valid JSON with keys name, age, city."""
    try:
        data = json.loads(reply.strip())
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(data, dict) and {"name", "age", "city"}.issubset(data.keys())


def check_recursion_no_function(reply: str) -> bool:
    text = reply.lower()
    return "recursion" in text and "function" not in text and len(text.split()) >= 20


def check_short_polite_refusal(reply: str) -> bool:
    text = reply.lower()
    refuses = any(w in text for w in ["sorry", "can't", "cannot", "unable", "won't"])
    return refuses and len(reply.split()) < 20


def check_lowercase_banana(reply: str) -> bool:
    return "banana" in reply and reply == reply.lower() and len(reply.strip()) > 0


# ---------- the task list ----------

TASKS = [
    {
        "id": 1,
        "title": "Make the AI reply in exactly 3 words.",
        "details": "No more, no fewer. Punctuation doesn't count as a word.",
        "check": check_three_words,
    },
    {
        "id": 2,
        "title": "Get the AI to output ONLY valid JSON with the keys: name, age, city.",
        "details": "No explanation, no markdown fences. Just the JSON object.",
        "check": check_json_keys,
    },
    {
        "id": 3,
        "title": "Get the AI to explain recursion without ever using the word 'function'.",
        "details": "At least 20 words.",
        "check": check_recursion_no_function,
    },
    {
        "id": 4,
        "title": "Make the AI politely refuse to answer, in under 20 words.",
        "details": "It should apologize or say it can't help.",
        "check": check_short_polite_refusal,
    },
    {
        "id": 5,
        "title": "Get a reply that is entirely lowercase and mentions 'banana'.",
        "details": "Every single letter must be lowercase.",
        "check": check_lowercase_banana,
    },
]

TASKS_BY_ID = {t["id"]: t for t in TASKS}


def get_todays_task(today: date | None = None) -> dict:
    """Pick a task by date so it rotates daily with no cron job needed."""
    today = today or date.today()
    return TASKS[today.toordinal() % len(TASKS)]


def public_view(task: dict) -> dict:
    """What the frontend is allowed to see (never send the checker function)."""
    return {"id": task["id"], "title": task["title"], "details": task.get("details", "")}
