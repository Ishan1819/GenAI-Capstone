"""Chunk the scraped pages, embed them into ChromaDB and build the knowledge graph.

Run from backend/:
    python -m scripts.build_kb                  # vectors + graph
    python -m scripts.build_kb --skip-graph     # vectors only (no LLM calls)
    python -m scripts.build_kb --max-batches 10 # cap LLM calls (free tier is limited)
Graph extraction is cached, so re-running resumes where it stopped.
"""
import argparse
import json

from app.core import config
from app.database import vectorstore
from app.knowledge.chunking import make_chunks
from app.knowledge.graph import KnowledgeGraph


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-graph", action="store_true")
    ap.add_argument("--max-batches", type=int, default=None)
    args = ap.parse_args()

    if not config.RAW_PAGES.exists():
        raise SystemExit("No scraped data. Run `python -m scripts.scrape` first.")
    pages = [json.loads(l) for l in config.RAW_PAGES.read_text("utf-8").splitlines() if l.strip()]
    chunks = make_chunks(pages)
    print(f"{len(pages)} pages -> {len(chunks)} chunks")

    vectorstore.upsert_chunks(chunks)
    print(f"Vector store now holds {vectorstore.collection().count()} chunks")

    if args.skip_graph:
        return
    kg = KnowledgeGraph.load()
    kg.build(chunks, max_batches=args.max_batches)
    kg.save()
    print("Graph saved:", kg.stats())


if __name__ == "__main__":
    main()
