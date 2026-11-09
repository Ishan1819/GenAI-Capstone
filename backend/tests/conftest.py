"""Shared fixtures for the functional tests (paper, Section 5.2, Table 8).

- The whole session runs on a FRESH COPY of backend/data (vector store, demo records, scraped pages) with an EMPTY
  SQLite log/queue, so the tests never touch live data (Section 4.7).
- Retrieval, ChromaDB and the MiniLM embeddings are REAL.
- The LLM is replaced by a deterministic fake that follows each prompt's contract, so the tests are fast, offline and
  repeatable. TC15 is the exception: it talks to a real, unreachable endpoint.

Prerequisites: build_kb and generate_demo_data have been run once (backend/data exists) and the embedding model is
cached locally.
"""
import os
import re

from app.core.isolation import use_fresh_copy  # must run before any other app import

use_fresh_copy(include_db=False)
os.environ["ADMIN_TOKEN"] = "test-admin-token"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import config, llm  # noqa: E402

config.ADMIN_TOKEN = "test-admin-token"
ADMIN = {"X-Admin-Token": "test-admin-token"}

STOP = {"what", "which", "does", "who", "whom", "whose", "where", "when", "how", "about", "with", "that", "this",
        "there", "their", "they", "them", "from", "have", "your", "into", "isdic", "tell", "please", "cover"}


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3 and w not in STOP}


class FakeLLM:
    """Stands in for llm.chat. Routes on the system prompt and answers the way a well-behaved model would."""

    def __init__(self):
        self.calls: list[dict] = []
        self.fail_on: set[str] = set()  # prompt kinds that should raise RuntimeError (provider down)
        self.search_reply: dict | None = None  # override for the search parser

    @staticmethod
    def kind(system: str) -> str:
        table = [("You are the ISDIC assistant", "chat"), ("Rewrite the user's last message", "condense"),
                 ("Convert a search request", "search"), ("You explain recommendations", "explain"),
                 ("You design learning roadmaps", "path"), ("multiple-choice quiz", "quiz"),
                 ("insight briefs", "insights"), ("Extract the technical skills", "resume_extract"),
                 ("You advise students", "resume")]
        return next((k for marker, k in table if marker in system), "other")

    def __call__(self, messages, **kwargs) -> str:
        import json

        system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        user = messages[-1]["content"]
        kind = self.kind(system)
        self.calls.append({"kind": kind, "user": user})
        if kind in self.fail_on:
            raise RuntimeError("LLM gave no answer after 4 tries (simulated outage)")

        if kind == "chat":
            q = user.rsplit("QUESTION:", 1)[-1]
            sources = re.findall(r"^\[(\d+)\][^\n]*\n(.*?)(?=^\[\d+\]|\Z)", user.split("QUESTION:")[0], re.M | re.S)
            want = content_words(q)
            best = max(((len(want & content_words(t)) / max(len(want), 1), int(n), t) for n, t in sources),
                       default=(0, 0, ""))
            if best[0] < 0.6:  # the sources don't cover the question
                return json.dumps({"grounded": False, "answer": "", "sources": [], "followups": []})
            sentence = re.split(r"(?<=[.!?])\s", best[2].strip())[0][:300]
            return json.dumps({"grounded": True, "answer": f"{sentence} [{best[1]}]", "sources": [best[1]],
                               "followups": ["What are the levels?", "Who can join?", "Where are the chapters?"]})
        if kind == "condense":
            convo = user.split("Last message:")[0]
            first_q = re.search(r"user: (.*)", convo).group(1)
            topic = "AI and ML" if re.search(r"\bAI\b", first_q) else first_q
            return f"Who mentors the {topic} community at ISDIC?"
        if kind == "search":
            return json.dumps(self.search_reply or {"entity_type": None, "domain": None, "chapter": None,
                                                    "level": None, "upcoming": False, "semantic_query": ""})
        if kind == "explain":
            keys = re.findall(r"^([a-z]\d+): ", user, re.M)
            return json.dumps({k: f"This fits you because of the shared evidence listed for {k}." for k in keys})
        if kind == "path":
            return json.dumps({"summary": "A roadmap from the supplied curriculum.", "steps": [
                {"order": 1, "title": "Level 01 foundations", "level": "Beginner", "why": "start here",
                 "skills_gained": ["NumPy"]},
                {"order": 2, "title": "Level 02 core ML", "level": "Intermediate", "why": "next", "skills_gained": []},
                {"order": 3, "title": "Level 03 projects", "level": "Advanced", "why": "then", "skills_gained": []}]})
        if kind == "quiz":
            n = int(re.search(r"Write (\d+) questions", user).group(1))
            return json.dumps({"questions": [{"question": f"Q{i}: what is Wireshark used for?",
                                              "options": ["Packet analysis", "Painting", "Cooking", "Gardening"],
                                              "answer_index": 0, "explanation": "It captures packets.",
                                              "topic": "Network Security"} for i in range(1, n + 1)]})
        if kind == "insights":
            return ("What members are asking: curriculum questions.\n"
                    "Knowledge gaps: hostel and refund questions.\n"
                    "Suggested actions: add an FAQ entry.")
        if kind == "resume_extract":
            return json.dumps({"skills": ["Python"], "interests": ["ML"]})
        if kind == "resume":
            return json.dumps({"recommended_domain": "AI and ML", "recommended_level": "Beginner", "summary": "ok"})
        return "{}"


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "chat", fake)  # chat_json calls llm.chat, so JSON prompts are faked too
    return fake


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:  # runs the lifespan (creates the SQLite schema)
        yield c
