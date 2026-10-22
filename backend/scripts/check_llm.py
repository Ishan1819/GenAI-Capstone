"""Quick check that the configured LLM (Ollama or an API) answers, and how fast.

Run from backend/:  python -m scripts.check_llm
"""
import time

from app.core import config, llm


def main() -> None:
    print(f"Model: {config.LLM_MODEL}  at  {config.LLM_BASE_URL}")
    start = time.time()
    text = llm.chat([{"role": "user", "content": "Reply with one short sentence: what is RAG?"}], max_tokens=100, retries=1)
    print(f"Plain reply ({time.time() - start:.1f}s): {text}")

    start = time.time()
    data = llm.chat_json([{"role": "user", "content": 'Return JSON: {"domains": [the 4 ISDIC-style tech domains: '
                                                       'cybersecurity, AI/ML, cloud/DevOps, software development]}'}],
                         max_tokens=200)
    print(f"JSON reply ({time.time() - start:.1f}s): {data}")
    print("LLM is working.")


if __name__ == "__main__":
    main()
