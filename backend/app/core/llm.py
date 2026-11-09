import json
import re
import threading
import time

from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, RateLimitError

from app.core import config


class LLMAuthError(RuntimeError):
    """Bad or missing API key; retrying won't help."""


_clients: dict[tuple[str, str], OpenAI] = {}
_lock = threading.Lock()
_last_call = 0.0


def _get_client(base_url: str | None = None, api_key: str | None = None) -> OpenAI:
    """Client for the main LLM, or for another OpenAI-compatible provider (e.g. a separate evaluation judge)."""
    url, key = base_url or config.LLM_BASE_URL, api_key or config.LLM_API_KEY
    if not key:
        raise RuntimeError("LLM_API_KEY is not set (copy .env.example to .env)")
    if (url, key) not in _clients:
        _clients[(url, key)] = OpenAI(base_url=url, api_key=key, timeout=config.LLM_TIMEOUT)
    return _clients[(url, key)]


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


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 4000, retries: int = 4,
         json_mode: bool = False, model: str | None = None, base_url: str | None = None,
         api_key: str | None = None) -> str:
    """One chat completion. Every provider failure ends as a RuntimeError, which the API maps to HTTP 503."""
    params = {"model": model or config.LLM_MODEL, "messages": messages, "temperature": temperature,
              "max_tokens": max_tokens}
    # Reasoning models (gpt-oss, etc.) can spend the whole token budget thinking and return no answer;
    # a low reasoning effort keeps room for the reply.
    if config.LLM_REASONING_EFFORT:
        params["extra_body"] = {"reasoning_effort": config.LLM_REASONING_EFFORT}
    if json_mode and config.LLM_JSON_MODE:
        params["response_format"] = {"type": "json_object"}
    delay, last_problem = 5.0, "unknown"
    for attempt in range(retries):
        _throttle()
        try:
            resp = _get_client(base_url, api_key).chat.completions.create(**params)
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
        except RuntimeError:  # configuration problem (e.g. no API key): retrying won't help
            raise
        except APIConnectionError as e:  # endpoint unreachable or timed out (TC15)
            last_problem = f"LLM endpoint unreachable: {getattr(e, 'message', e)}"
        except APIError as e:
            last_problem = f"API error: {getattr(e, 'message', e)}"
        except Exception as e:  # anything else from the client library must not surface as HTTP 500
            last_problem = f"{type(e).__name__}: {e}"
        if attempt == retries - 1:
            break
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
    """JSON reply; one self-correction prompt if the first reply is not valid JSON."""
    try:
        return parse_json(chat(messages, json_mode=True, **kwargs))
    except (ValueError, json.JSONDecodeError):
        retry = messages + [{"role": "user", "content": "Your reply was not valid JSON. Reply with only the JSON object."}]
        try:
            return parse_json(chat(retry, json_mode=True, **kwargs))
        except (ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(f"LLM did not return valid JSON: {e}")
