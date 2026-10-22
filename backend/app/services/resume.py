"""Resume / skill-gap analyser: maps a resume onto ISDIC's domains, levels and modules."""
import io

from pypdf import PdfReader

from app.core import llm
from app.rag import retrieval

MAX_CHARS = 6000

EXTRACT_SYSTEM = ('Extract the technical skills, tools and interests from this resume. '
                  'Reply with JSON only: {"skills": ["..."], "interests": ["..."]}')

SYSTEM = """You advise students on which ISDIC programme fits them, using ONLY the supplied ISDIC curriculum.
Compare the resume skills against the curriculum. Do not recommend modules that are not in the curriculum text.
Reply with JSON only:
{"recommended_domain": "...", "recommended_level": "Beginner|Intermediate|Advanced",
 "level_reason": "...", "matched_skills": ["..."], "missing_skills": ["..."],
 "recommended_modules": [{"name": "...", "reason": "..."}], "summary": "2-3 sentences"}"""


def read_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


def analyse(text: str) -> dict:
    text = text.strip()[:MAX_CHARS]
    if len(text) < 50:
        raise ValueError("Could not read enough text from the resume (scanned PDFs are not supported).")

    ext = llm.chat_json([{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": text}])
    skills, interests = ext.get("skills", []), ext.get("interests", [])

    r = retrieval.retrieve(" ".join(skills + interests) + " ISDIC curriculum domains levels modules", k=8)
    context = (f"RESUME SKILLS: {', '.join(skills)}\nINTERESTS: {', '.join(interests)}\n\n"
               "ISDIC CURRICULUM:\n" + "\n\n".join(c["text"] for c in r["contexts"]))

    out = llm.chat_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": context}])
    out["detected_skills"] = skills
    out["sources"] = [{"title": c["title"], "url": c["url"]} for c in r["contexts"] if c["url"]]
    return out
