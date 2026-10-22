import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core import config

_collection = None
_ef = None


def _embedding_fn():
    global _ef
    if _ef is None:
        _ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBED_MODEL)
    return _ef


def collection():
    global _collection
    if _collection is None:
        config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = client.get_or_create_collection(
            "isdic_kb", embedding_function=_embedding_fn(), metadata={"hnsw:space": "cosine"}
        )
    return _collection


def embed(texts: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in _embedding_fn()(texts)]


def upsert_chunks(chunks: list[dict], batch: int = 64) -> None:
    col = collection()
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        col.upsert(
            ids=[c["id"] for c in part],
            documents=[c["text"] for c in part],
            metadatas=[c["metadata"] for c in part],
        )


def delete_where(where: dict) -> None:
    collection().delete(where=where)


def search(query: str, k: int = 6, where: dict | None = None) -> list[dict]:
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_texts=[query], n_results=min(k, col.count()), where=where)
    return [
        {"id": i, "text": d, "metadata": m, "distance": dist}
        for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def get_by_ids(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    res = collection().get(ids=ids)
    return [{"id": i, "text": d, "metadata": m} for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])]


def get_where(where: dict) -> list[dict]:
    res = collection().get(where=where)
    return [{"id": i, "text": d, "metadata": m} for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])]


def sample_chunks(n: int) -> list[dict]:
    import random

    res = collection().get()
    rows = list(zip(res["ids"], res["documents"], res["metadatas"]))
    random.shuffle(rows)
    return [{"id": i, "text": d, "metadata": m} for i, d, m in rows[:n]]
