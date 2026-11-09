"""RAG retrieval over the ChromaDB knowledge base: Eq. (2) of the paper.

    Ctx(q) = top_k { c in V : d(q, c) <= tau  AND  phi(c) }

d is the cosine distance between normalised MiniLM embeddings, tau the distance threshold and phi a metadata filter
predicate (domain, chapter, level, entity type, date).
"""
from app.core import config
from app.database import vectorstore

DEFAULT_WHERE = {"source": {"$ne": "member"}}  # member profiles would crowd out curriculum content


def retrieve(query: str, k: int = 6, where: dict | None = None, max_distance: float | None = None) -> dict:
    """Top-k chunks within the distance threshold that satisfy the filter. Members excluded unless `where` says so."""
    tau = config.MAX_DISTANCE if max_distance is None else max_distance
    hits = vectorstore.search(query, k=k, where=where or DEFAULT_WHERE)
    best = hits[0]["distance"] if hits else None
    contexts = [{
        "id": h["id"],
        "text": h["text"],
        "title": h["metadata"].get("title", ""),
        "url": h["metadata"].get("url", ""),
        "metadata": h["metadata"],
        "distance": round(h["distance"], 4),
        "score": round(1 - h["distance"], 3),
    } for h in hits if h["distance"] <= tau]
    return {"contexts": contexts, "sufficient": bool(contexts), "best_distance": best}


def plain_retrieve(query: str, k: int = 6, max_distance: float | None = None) -> dict:
    """Plain vector RAG baseline: similarity only, over ALL chunks (members included), no filter predicate."""
    return retrieve(query, k=k, where=_ALL, max_distance=max_distance)


_ALL = {"source": {"$in": ["web", "faq", "member", "event"]}}  # every chunk: no attribute predicate


def filters_for(query: str) -> dict | None:
    """phi(c) for a question about members or events that names a domain, chapter or level; None otherwise."""
    from app.services import search  # local import: search depends on the LLM layer

    f = search.parse_rules(query)
    if f["entity_type"] not in ("member", "event"):
        return None
    if not any(f.get(x) for x in ("domain", "chapter", "level")) and not f.get("upcoming"):
        return None
    return f


def filtered_retrieve(query: str, f: dict, k: int | None = None, max_distance: float | None = None) -> dict:
    """Metadata-filtered retrieval: the parsed filters become the predicate phi in Eq. (2)."""
    from app.services import search

    r = retrieve(query, k=k or config.FILTERED_K, where=search.build_where(f), max_distance=max_distance)
    r["filters"] = {x: f.get(x) for x in ("entity_type", "domain", "chapter", "level", "upcoming") if f.get(x)}
    return r
