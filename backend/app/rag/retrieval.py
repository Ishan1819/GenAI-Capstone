"""RAG retrieval: semantic search over the ChromaDB knowledge base."""
from app.core import config
from app.database import vectorstore


def retrieve(query: str, k: int = 6, where: dict | None = None) -> dict:
    """Top-k relevant chunks. Member profiles are excluded by default so they don't crowd out ISDIC content."""
    hits = vectorstore.search(query, k=k, where=where or {"source": {"$ne": "member"}})
    best = hits[0]["distance"] if hits else None
    contexts = [{
        "id": h["id"],
        "text": h["text"],
        "title": h["metadata"].get("title", ""),
        "url": h["metadata"].get("url", ""),
        "score": round(1 - h["distance"], 3),
    } for h in hits if h["distance"] <= config.MAX_DISTANCE]
    return {"contexts": contexts, "sufficient": bool(contexts), "best_distance": best}
