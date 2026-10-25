"""
tasks.py  (owner: Data + pitch person writes tasks, Backend person writes checkers)

Each task has:
  - id:         unique int
  - difficulty: "easy", "medium", or "hard"
  - title:      short text shown to the player
  - details:    optional extra explanation
  - answer:     the exact text the reply must equal (after trimming whitespace)
      OR
  - check:      function(reply: str) -> bool, for tasks with no single exact answer

HOW TO ADD A TASK: if there's one exact answer, just set "answer".
Otherwise write a checker function and set "check".
Keep checkers simple and deterministic (regex, json.loads, word counts).

THE NO-COPYING RULE: a reply never passes if the player typed it themselves
in one of their prompts. Otherwise every task is solved by "Say exactly: <answer>".
"""
import csv
import io
import json
import os
import re
from datetime import date


# ---------- checker functions (for tasks without one exact answer) ----------

def _parse_json(text: str):
    """Return the parsed JSON, or None if it isn't valid JSON."""
    try:
        return json.loads(text.strip())
    except ValueError:
        return None


def check_three_lines(reply: str) -> bool:
    lines = [line.strip() for line in reply.strip().splitlines()]
    return lines == ["red", "green", "blue"]


def check_numbers(reply: str) -> bool:
    # Spaces are ignored so "7, 14, 2" also counts
    return reply.strip().replace(" ", "") == "7,14,2"


def check_sorted_fruits(reply: str) -> bool:
    return reply.strip().replace(" ", "") == "apple,banana,kiwi,pear"


def check_json_nova(reply: str) -> bool:
    return _parse_json(reply) == {"name": "Nova", "level": 3}


def check_csv_row(reply: str) -> bool:
    rows = list(csv.reader(io.StringIO(reply.strip()), skipinitialspace=True))
    return rows == [["Smith, Jane", "19", "New York"]]


def check_star_acrostic(reply: str) -> bool:
    lines = [line for line in reply.strip().splitlines() if line.strip()]
    if len(lines) != 4:
        return False
    if any(len(line.split()) != 3 for line in lines):
        return False
    initials = "".join(line.split()[0][0] for line in lines)
    return initials.upper() == "STAR"


def check_no_letter_e(reply: str) -> bool:
    text = reply.strip()
    return len(text.split()) >= 8 and "e" not in text.lower() and text[-1:] in ".!?"


def check_twenty_words(reply: str) -> bool:
    return len(reply.split()) == 20 and "team" in reply.lower()


def check_squares(reply: str) -> bool:
    return _parse_json(reply) == [1, 4, 9, 16, 25]


def check_status_and_array(reply: str) -> bool:
    lines = reply.strip().splitlines()
    return (
        len(lines) == 2
        and lines[0].strip() == "STATUS: OK"
        and _parse_json(lines[1]) == [2, 4, 6]
    )


def check_sorted_people(reply: str) -> bool:
    return _parse_json(reply) == [
        {"name": "Ben", "age": 19},
        {"name": "Cy", "age": 21},
        {"name": "Ada", "age": 22},
    ]


# ---------- the task list ----------

TASKS = [
    # ----- easy -----
    {
        "id": 1,
        "difficulty": "easy",
        "title": "Get the AI to output exactly: READY FOR LAUNCH",
        "details": "Nothing else in the reply.",
        "answer": "READY FOR LAUNCH",
    },
    {
        "id": 2,
        "difficulty": "easy",
        "title": "Ask the AI for the capital of France. Its entire reply must be a single lowercase word.",
        "details": "",
        "answer": "paris",
    },
    {
        "id": 3,
        "difficulty": "easy",
        "title": "Make the AI produce precisely these lines, in this order: red / green / blue.",
        "details": "One word per line, no other text.",
        "check": check_three_lines,
    },
    {
        "id": 4,
        "difficulty": "easy",
        "title": "Make the AI reverse the characters in the string \"stressed\". Return only the result.",
        "details": "",
        "answer": "desserts",
    },
    {
        "id": 5,
        "difficulty": "easy",
        "title": "From \"Order A12: 7 apples, 14 pears, 2 plums\", return only the quantities in source order, separated by commas.",
        "details": "",
        "check": check_numbers,
    },
    {
        "id": 6,
        "difficulty": "easy",
        "title": "Sort these lowercase words alphabetically: kiwi, apple, pear, banana. Output one comma-separated line.",
        "details": "",
        "check": check_sorted_fruits,
    },
    {
        "id": 7,
        "difficulty": "easy",
        "title": "Normalize \" HeLLo, WoRLD! \" to lowercase and collapse redundant spaces. Output only the cleaned text.",
        "details": "",
        "answer": "hello, world!",
        # The task's own input is the answer in different capitals, so only an
        # exact-capitals copy counts as cheating here (pasting the input is fine).
        "echo_case_sensitive": True,
    },
    {
        "id": 8,
        "difficulty": "easy",
        "title": "Decode the ASCII binary groups 01000011 01000001 01010100 and output only the decoded word.",
        "details": "",
        "answer": "CAT",
    },
    # ----- medium -----
    {
        "id": 9,
        "difficulty": "medium",
        "title": "Return a valid JSON object with exactly two keys, \"name\" and \"level\", set to \"Nova\" and 3.",
        "details": "No markdown, no code fences, no extra keys.",
        "check": check_json_nova,
    },
    {
        "id": 10,
        "difficulty": "medium",
        "title": "Create a CSV record of three fields: \"Smith, Jane\", 19, and \"New York\". Quote fields when needed.",
        "details": "Exactly one row, nothing else.",
        "check": check_csv_row,
    },
    {
        "id": 11,
        "difficulty": "medium",
        "title": "Convert \"October 24, 2026\" into ISO date format. Reply with the date only.",
        "details": "",
        "answer": "2026-10-24",
    },
    {
        "id": 12,
        "difficulty": "medium",
        "title": "Get a lowercase English word that uses every letter of \"listen\" exactly once and means \"quiet\".",
        "details": "Only the word.",
        "answer": "silent",
    },
    {
        "id": 13,
        "difficulty": "medium",
        "title": "Get four lines whose first words begin with S, T, A, R. Each line must be exactly three words.",
        "details": "No blank-line tricks: exactly four lines with text.",
        "check": check_star_acrostic,
    },
    {
        "id": 14,
        "difficulty": "medium",
        "title": "Get a grammatical sentence of at least 8 words that never uses the letter \"e\".",
        "details": "Upper or lowercase. It must end with . ! or ?",
        "check": check_no_letter_e,
    },
    {
        "id": 15,
        "difficulty": "medium",
        "title": "Get a cheerful message about teamwork that is exactly 20 words long.",
        "details": "Words are counted by spaces. Must include \"team\" or \"teamwork\".",
        "check": check_twenty_words,
    },
    {
        "id": 16,
        "difficulty": "medium",
        "title": "Is 29 prime? Get the AI to answer with a single uppercase word.",
        "details": "Nothing else in the reply.",
        "answer": "YES",
        # Yes/no question: "answer YES or NO" is a fair prompt, not copying.
        "allow_echo": True,
    },
    {
        "id": 17,
        "difficulty": "medium",
        "title": "Give XOR outputs for (A,B) = (0,0), (0,1), (1,0), (1,1). Return only the 4 digits.",
        "details": "",
        "answer": "0110",
    },
    {
        "id": 18,
        "difficulty": "medium",
        "title": "Count the vowels (a, e, i, o, u) in \"PROMPT ENGINEERING\". Output only the number.",
        "details": "",
        "answer": "6",
    },
    {
        "id": 19,
        "difficulty": "medium",
        "title": "Return a JSON array of the squares of the integers 1 through 5, in ascending order.",
        "details": "Nothing else in the reply.",
        "check": check_squares,
    },
    {
        "id": 20,
        "difficulty": "medium",
        "title": "Classify 3, 8, 11, 14 as odd/even. Return one lowercase label per number, separated by pipes (|).",
        "details": "",
        "answer": "odd|even|odd|even",
    },
    # ----- hard -----
    {
        "id": 21,
        "difficulty": "hard",
        "title": "Get exactly two lines. Line 1 is \"STATUS: OK\". Line 2 is the JSON array [2,4,6].",
        "details": "No explanations, no code fences.",
        "check": check_status_and_array,
    },
    {
        "id": 22,
        "difficulty": "hard",
        "title": "Get the lowercase English alphabet without a, e, i, o, u, as one unbroken string.",
        "details": "",
        "answer": "bcdfghjklmnpqrstvwxyz",
    },
    {
        "id": 23,
        "difficulty": "hard",
        "title": "Return a JSON array of objects for Ada age 22, Ben age 19, and Cy age 21, sorted by age ascending.",
        "details": "Keys must be \"name\" and \"age\" only. No code fences, nothing else in the reply.",
        "check": check_sorted_people,
    },
    {
        "id": 24,
        "difficulty": "hard",
        "title": "Convert \"two seven zero five\" into digits, with a hyphen after the second digit. Output only the result.",
        "details": "",
        "answer": "27-05",
    },
    {
        "id": 25,
        "difficulty": "hard",
        "title": "Transform \"a1 b22 c333\": uppercase each letter and repeat it once per digit after it. Separate groups with colons.",
        "details": "",
        "answer": "A:BB:CCC",
    },
]

TASKS_BY_ID = {t["id"]: t for t in TASKS}


# ---------- judging a reply ----------

def _contains_phrase(text: str, phrase: str, case_sensitive: bool) -> bool:
    """True if phrase appears in text as whole words ("cat" is not in "concatenate")."""
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text, flags) is not None


def copied_from_prompts(task: dict, reply: str, prompts: list[str]) -> bool:
    """True if the player typed the AI's reply themselves in any of their prompts."""
    # Collapse all whitespace so line breaks and double spaces don't hide a copy
    reply = " ".join(reply.split())
    if not reply or task.get("allow_echo"):
        return False
    case_sensitive = task.get("echo_case_sensitive", False)
    return any(
        _contains_phrase(" ".join(p.split()), reply, case_sensitive) for p in prompts
    )


def is_passing(task: dict, reply: str, prompts: list[str]) -> bool:
    """Did this reply solve the task? prompts = everything the player typed this round."""
    if "answer" in task:
        correct = reply.strip() == task["answer"]
    else:
        correct = bool(task["check"](reply))
    return correct and not copied_from_prompts(task, reply, prompts)


def get_todays_task(today: date | None = None) -> dict:
    """Pick a task by date so it rotates daily with no cron job needed.

    Set TASK_ID in .env (e.g. TASK_ID=14) to pin one task, handy for the demo.
    """
    pinned = os.getenv("TASK_ID", "").strip()
    if pinned:
        if pinned.isdigit() and int(pinned) in TASKS_BY_ID:
            return TASKS_BY_ID[int(pinned)]
        print(f"[tasks] TASK_ID={pinned!r} isn't a valid task id - using today's task instead")
    today = today or date.today()
    return TASKS[today.toordinal() % len(TASKS)]


def public_view(task: dict) -> dict:
    """What the frontend is allowed to see (never send the answer or checker)."""
    return {"id": task["id"], "title": task["title"], "details": task.get("details", "")}
