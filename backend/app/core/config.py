import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# DATA_DIR can point at a throw-away copy so tests and experiments never touch the live data (see app/core/isolation.py)
DATA_DIR = Path(os.getenv("DATA_DIR") or BASE_DIR / "data")
RAW_PAGES = DATA_DIR / "raw" / "pages.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
DB_PATH = DATA_DIR / "app.db"
EVAL_DIR = BASE_DIR / "data" / "eval"  # always the live folder, so results survive isolated runs
DEMO_DIR = DATA_DIR / "demo"

SITE_URL = os.getenv("SITE_URL", "https://isdic.in")
MAX_PAGES = int(os.getenv("MAX_PAGES", "80"))

# Any OpenAI-compatible provider works; OPENROUTER_API_KEY is still accepted for old .env files
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free")
LLM_MIN_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL", "3.5"))
# "low" | "medium" | "high" for reasoning models such as gpt-oss; set empty for providers that reject it
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")
# Ask the server for strict JSON output where we need JSON (Ollama, OpenAI, Groq support it); helps small models
LLM_JSON_MODE = os.getenv("LLM_JSON_MODE", "false").lower() == "true"
# Seconds to wait for one reply; local models on a CPU can be slow
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "600"))
# Evaluation judge (scripts/evaluate.py). Empty = same provider/model as the generator.
# E.g. generate with local Ollama but judge with Groq gpt-oss-20b, as in the paper.
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "")
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY", "")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "")
EMBED_MODEL =os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.65"))  # tau in Eq. (2)
CHAT_K = int(os.getenv("CHAT_K", "4"))  # k for the chatbot's default retrieval
FILTERED_K = int(os.getenv("FILTERED_K", "6"))  # k for metadata-filtered member/event questions
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
