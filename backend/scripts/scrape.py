"""Crawl isdic.in (same domain only) and save cleaned page text to data/raw/pages.jsonl.

Run from backend/:  python -m scripts.scrape
"""
import json
import re
import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ISDIC-Capstone-Bot/1.0; academic project)"}
SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".mp4", ".css", ".js", ".ico", ".xml")
TEXT_TAGS = ["h1", "h2", "h3", "h4", "p", "li", "td", "th", "dt", "dd", "blockquote"]
DELAY = 1.0


def normalise(url: str) -> str:
    url, _ = urldefrag(url)
    return url.split("?")[0].rstrip("/")


def same_site(url: str, root: str) -> bool:
    host = lambda u: urlparse(u).netloc.removeprefix("www.")
    return host(url) == host(root)


def extract(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""

    lines, last = [], ""
    for el in soup.find_all(TEXT_TAGS):
        if el.find(TEXT_TAGS):  # only take leaf blocks so text isn't duplicated
            continue
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if not text or text == last:
            continue
        lines.append(f"## {text}" if el.name in ("h1", "h2", "h3", "h4") else text)
        last = text
    body = "\n".join(lines)
    if len(body) < 200:  # unusual markup: fall back to all visible text
        body = "\n".join(t for t in soup.get_text("\n", strip=True).splitlines() if t.strip())
    return title, body


def sitemap_urls(root: str) -> list[str]:
    try:
        r = requests.get(urljoin(root, "/sitemap.xml"), headers=HEADERS, timeout=15)
        if r.ok:
            return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
    except requests.RequestException:
        pass
    return []


def crawl(root: str, max_pages: int) -> list[dict]:
    root = normalise(root)
    queue = deque([root, *map(normalise, sitemap_urls(root))])
    seen, pages = set(), []

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if url in seen or not same_site(url, root) or url.lower().endswith(SKIP_EXT):
            continue
        seen.add(url)
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            print(f"  ! {url}: {e}")
            continue
        if not r.ok or "text/html" not in r.headers.get("content-type", ""):
            continue

        title, body = extract(r.text)
        if body:
            pages.append({"url": url, "title": title or url, "text": body})
            print(f"[{len(pages):>3}] {url}  ({len(body)} chars)")

        for a in BeautifulSoup(r.text, "lxml").find_all("a", href=True):
            link = normalise(urljoin(url, a["href"]))
            if link.startswith("http") and link not in seen:
                queue.append(link)
        time.sleep(DELAY)
    return pages


def main() -> None:
    pages = crawl(config.SITE_URL, config.MAX_PAGES)
    config.RAW_PAGES.parent.mkdir(parents=True, exist_ok=True)
    with open(config.RAW_PAGES, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    total = sum(len(p["text"]) for p in pages)
    print(f"\nSaved {len(pages)} pages, {total} characters -> {config.RAW_PAGES}")
    if total < 3000:
        print("WARNING: very little text. The site is probably rendered with JavaScript; "
              "tell me and I'll switch the scraper to Playwright.")


if __name__ == "__main__":
    main()
