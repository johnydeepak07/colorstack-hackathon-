"""
llm.py  (owner: Backend/AI person)

ask(history) -> str
  history = [{"role": "user"|"assistant", "content": "..."}, ...]

If no ANTHROPIC_API_KEY is set, returns a fake reply so the whole app still runs.
To use OpenAI instead, rewrite the body of ask() - keep the same signature
so nothing else has to change.
"""
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")  # cheap + fast is fine for a game

SYSTEM_PROMPT = (
    "You are a helpful assistant in a prompt-engineering game. "
    "Follow the player's instructions as literally as you can."
)


def ask(history: list[dict]) -> str:
    if not API_KEY:
        return "(fake reply - set ANTHROPIC_API_KEY in .env for the real AI)"

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,      # keep replies short = cheaper + faster
        system=SYSTEM_PROMPT,
        messages=history,
    )
    return response.content[0].text
