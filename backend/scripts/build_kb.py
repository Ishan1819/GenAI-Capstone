"""Build the RAG knowledge base: chunk the scraped pages and embed them into ChromaDB (no LLM calls).

Everything is saved in backend/data/chroma, so run this once (or after re-scraping), not every time you start the app.

Run from backend/:  python -m scripts.build_kb
"""
import json

from app.core import config
from app.database import vectorstore
from app.knowledge.chunking import make_chunks


def main() -> None:
    if not config.RAW_PAGES.exists():
        raise SystemExit("No scraped data. Run `python -m scripts.scrape` first.")
    pages = [json.loads(l) for l in config.RAW_PAGES.read_text("utf-8").splitlines() if l.strip()]
    chunks = make_chunks(pages)
    print(f"{len(pages)} pages -> {len(chunks)} chunks")

    vectorstore.delete_where({"source": "web"})  # drop chunks of pages that no longer exist
    vectorstore.upsert_chunks(chunks)
    print(f"Vector store now holds {vectorstore.collection().count()} chunks (saved in {config.CHROMA_DIR})")


if __name__ == "__main__":
    main()
