import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
RAW_PAGES = DATA_DIR / "raw" / "pages.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
GRAPH_PATH = DATA_DIR / "graph.json"
EXTRACTION_CACHE = DATA_DIR / "extraction_cache.json"
DB_PATH = DATA_DIR / "app.db"
EVAL_DIR = DATA_DIR / "eval"
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
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.65"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
