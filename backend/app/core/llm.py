import json
import re
import threading
import time

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from app.core import config


class LLMAuthError(RuntimeError):
    """Bad or missing API key; retrying won't help."""


_client = None
_lock = threading.Lock()
_last_call = 0.0


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is not set (copy .env.example to .env)")
        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
    return _client


def _throttle() -> None:
    """Keep calls spaced out so the free tier's per-minute limit isn't hit."""
    global _last_call
    with _lock:
        wait = config.LLM_MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()


def _retry_after(err: RateLimitError, default: float) -> float:
    try:
        return float(err.response.headers.get("retry-after", default))
    except (AttributeError, TypeError, ValueError):
        return default


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 4000, retries: int = 4) -> str:
    # Reasoning models (gpt-oss, etc.) can spend the whole token budget thinking and return no answer;
    # a low reasoning effort keeps room for the reply.
    extra = {"reasoning_effort": config.LLM_REASONING_EFFORT} if config.LLM_REASONING_EFFORT else None
    delay, last_problem = 5.0, "unknown"
    for attempt in range(retries):
        _throttle()
        try:
            resp = _get_client().chat.completions.create(
                model=config.LLM_MODEL, messages=messages, temperature=temperature,
                max_tokens=max_tokens, extra_body=extra,
            )
            choice = resp.choices[0]
            text = (choice.message.content or "").strip()
            if text:
                return text
            last_problem = f"empty reply (finish_reason={choice.finish_reason})"
        except AuthenticationError:
            raise LLMAuthError("The LLM provider rejected the API key (401). Create a new key and put it in "
                               "backend/.env (LLM_API_KEY)")
        except RateLimitError as e:
            last_problem = f"rate limited: {getattr(e, 'message', e)}"
            delay = max(delay, _retry_after(e, delay))
        except APIError as e:
            last_problem = f"API error: {getattr(e, 'message', e)}"
            if attempt == retries - 1:
                raise
        print(f"    LLM attempt {attempt + 1}/{retries}: {last_problem}; retrying in {delay:.0f}s")
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"LLM gave no answer after {retries} tries ({last_problem})")


def parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON found in LLM reply")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


def chat_json(messages: list[dict], **kwargs):
    try:
        return parse_json(chat(messages, **kwargs))
    except (ValueError, json.JSONDecodeError):
        retry = messages + [{"role": "user", "content": "Your reply was not valid JSON. Reply with only the JSON object."}]
        return parse_json(chat(retry, **kwargs))
