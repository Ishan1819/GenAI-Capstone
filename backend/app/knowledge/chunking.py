import hashlib


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    parts = []
    for line in (l.strip() for l in text.split("\n")):
        while len(line) > size:  # very long paragraph: hard split
            parts.append(line[:size])
            line = line[size:]
        if line:
            parts.append(line)

    chunks, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) + 1 > size:
            chunks.append(cur)
            tail = cur[-overlap:].split(" ", 1)[-1]  # start overlap on a word boundary
            cur = f"{tail}\n{p}"
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def make_chunks(pages: list[dict]) -> list[dict]:
    out = []
    for page in pages:
        for i, text in enumerate(chunk_text(page["text"])):
            cid = hashlib.sha1(f"{page['url']}#{i}".encode()).hexdigest()[:16]
            out.append({
                "id": cid,
                "text": text,
                "metadata": {"url": page["url"], "title": page["title"], "chunk": i, "source": "web"},
            })
    return out
