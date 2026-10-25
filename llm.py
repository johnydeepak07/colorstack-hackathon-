"""
llm.py  (owner: Backend/AI person)

ask(history) -> str
  history = [{"role": "user"|"assistant", "content": "..."}, ...]
  Raises LLMError with a player-friendly message if the AI call fails.

If no GROQ_API_KEY is set, returns a fake reply so the whole app still runs.
To use a different provider, rewrite the body of ask() - keep the same signature
so nothing else has to change.
"""
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")  # cheap + fast is fine for a game

SYSTEM_PROMPT = (
    "You are a helpful assistant in a prompt-engineering game. "
    "Follow the player's instructions as literally as you can."
)


class LLMError(Exception):
    """The AI call failed. str(error) is safe to show to the player."""


_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=API_KEY, timeout=20, max_retries=1)
    return _client


def ask(history: list[dict]) -> str:
    if not API_KEY:
        return "(fake reply - set GROQ_API_KEY in .env for the real AI)"

    try:
        import groq
    except ImportError as e:
        print("[llm] groq isn't installed for this Python. Activate the venv, run "
              "`pip install -r requirements.txt`, and start with `python -m uvicorn main:app --reload`")
        raise LLMError("The server is missing the groq package. Check the server terminal.") from e

    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_completion_tokens=1000,  # gpt-oss models spend part of this on hidden reasoning
            reasoning_effort="low",      # gpt-oss only; remove both reasoning args for other models
            include_reasoning=False,
        )
    except groq.RateLimitError as e:
        raise LLMError("The AI is getting too many requests. Wait a few seconds and try again.") from e
    except groq.APITimeoutError as e:
        raise LLMError("The AI took too long to answer. Try again.") from e
    except groq.APIConnectionError as e:
        raise LLMError("Couldn't reach the AI. Check the server's internet connection.") from e
    except (groq.AuthenticationError, groq.PermissionDeniedError) as e:
        print(f"[llm] auth error - check GROQ_API_KEY: {e}")
        raise LLMError("The AI isn't configured correctly. Tell the organizers.") from e
    except groq.APIError as e:
        print(f"[llm] Groq API error: {e}")
        raise LLMError("The AI had a problem answering. Try again.") from e

    reply = response.choices[0].message.content or ""
    if not reply.strip():
        raise LLMError("The AI returned an empty reply. Try again.")
    return reply
