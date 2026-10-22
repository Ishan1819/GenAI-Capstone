"""Community records (members, events) and the shared vocabulary used by search and recommendations.

The records are demo data from scripts/generate_demo_data.py, stored as JSON in data/demo/.
"""
import json
from datetime import date
from functools import lru_cache

from app.core import config

LEVELS = ["Beginner", "Intermediate", "Advanced"]
LEVEL_RANK = {lvl: i for i, lvl in enumerate(LEVELS)}
LEVEL_ALIASES = {
    "Beginner": ["beginner", "beginners", "foundation", "beginner friendly", "basic", "basics", "intro", "introductory", "newbie", "starter"],
    "Intermediate": ["intermediate"],
    "Advanced": ["advanced", "expert", "experienced"],
}

DOMAINS = {
    "Cybersecurity": {
        "aliases": ["cybersecurity", "cyber security", "cyber", "security", "ctf", "hacking", "pentest", "ethical hacking"],
        "curriculum_page": "Cybersecurity curriculum | ISDIC",
        "skills": ["Network Security", "Linux", "Wireshark", "Burp Suite", "Penetration Testing", "Cryptography",
                   "SIEM", "OWASP Top 10", "Python", "Incident Response"],
    },
    "AI and ML": {
        "aliases": ["ai and ml", "ai ml", "aiml", "ai/ml", "ai-ml", "ai & ml", "ai&ml", "ai", "ml", "machine learning",
                    "artificial intelligence", "deep learning", "data science", "genai", "generative ai", "llm"],
        "curriculum_page": "AI & ML curriculum | ISDIC",
        "skills": ["Python", "NumPy", "Pandas", "Scikit-learn", "PyTorch", "TensorFlow", "NLP", "Computer Vision",
                   "LLMs", "MLOps"],
    },
    "Cloud and DevOps": {
        "aliases": ["cloud and devops", "cloud", "devops", "aws", "azure", "docker", "kubernetes"],
        "curriculum_page": "Cloud & DevOps curriculum | ISDIC",
        "skills": ["Linux", "AWS", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD", "Jenkins", "Ansible",
                   "Monitoring"],
    },
    "Software Development": {
        "aliases": ["software development", "software", "web development", "web", "app development", "full stack",
                    "frontend", "backend", "developer", "programming", "coding"],
        "curriculum_page": "Developer community curriculum | ISDIC",
        "skills": ["Java", "Python", "JavaScript", "React", "Node.js", "SQL", "Git", "REST APIs", "Spring Boot",
                   "System Design"],
    },
}

@lru_cache
def _load(name: str) -> list[dict]:
    path = config.DEMO_DIR / f"{name}.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else []

def reload() -> None:
    _load.cache_clear()

def members() -> list[dict]:
    return _load("members")

def events() -> list[dict]:
    return _load("events")

def member(member_id: str) -> dict | None:
    return next((m for m in members() if m["id"] == member_id), None)

def is_upcoming(ev: dict) -> bool:
    return ev["date"] >= date.today().isoformat()

def member_text(m: dict) -> str:
    return (f"{m['name']} ({m['role']}) is a {m['level']} member of the ISDIC {m['domain']} community, "
            f"{m['chapter']} chapter, studying at {m['college']}. Skills: {', '.join(m['skills'])}. "
            f"Interests: {', '.join(m['interests'])}. Joined {m['joined']}.")

def event_text(e: dict) -> str:
    return (f"{e['name']}: a {e['level']}-level {e['type']} by the ISDIC {e['domain']} community at the "
            f"{e['chapter']} chapter on {e['date']} ({e['mode']}). Covers {', '.join(e['skills'])}. {e['description']}")

def to_chunks() -> list[dict]:
    """Records as documents for the vector store; metadata carries the structured filter fields."""
    chunks = []
    for m in members():
        chunks.append({"id": f"member-{m['id']}", "text": member_text(m), "metadata": {
            "source": "member", "entity_id": m["id"], "title": m["name"], "url": "",
            "domain": m["domain"], "chapter": m["chapter"], "level": m["level"], "skills": ", ".join(m["skills"])}})
    for e in events():
        chunks.append({"id": f"event-{e['id']}", "text": event_text(e), "metadata": {
            "source": "event", "entity_id": e["id"], "title": e["name"], "url": "",
            "domain": e["domain"], "chapter": e["chapter"], "level": e["level"], "skills": ", ".join(e["skills"]),
            "date": e["date"], "date_int": int(e["date"].replace("-", "")), "event_type": e["type"]}})
    return chunks

def vocabulary() -> dict:
    chapters = sorted({m["chapter"] for m in members()} | {e["chapter"] for e in events()})
    return {"entity_types": ["member", "event", "page"], "domains": list(DOMAINS), "chapters": chapters, "levels": LEVELS}
