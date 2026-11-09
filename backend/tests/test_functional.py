"""Sixteen functional and edge-case tests, TC01-TC16 (paper, Table 8). Run from backend/:  python -m pytest -v"""
import json

import pytest

from app.core import config, llm
from app.database import community, db, vectorstore
from tests.conftest import ADMIN


# ---------------------------------------------------------------- Chatbot
def test_TC01_chatbot_grounded_answer_with_citation(client, fake_llm):
    r = client.post("/api/chat", json={"message": "What does the Cloud & DevOps track cover?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answered"] is True
    assert body["sources"], "a grounded answer must cite at least one retrieved source (Eq. 3)"
    assert any(f"[{s['n']}]" in body["answer"] for s in body["sources"])


def test_TC02_chatbot_out_of_scope_refused_and_queued(client, fake_llm):
    q = "What is the capital of France?"
    r = client.post("/api/chat", json={"message": q})
    assert r.status_code == 200
    body = r.json()
    assert body["answered"] is False
    assert body["sources"] == []
    assert "don't want to guess" in body["answer"]  # fallback message, never a guess
    assert any(item["question"] == q for item in db.list_unanswered("open"))


def test_TC03_chatbot_follow_up_is_condensed(client, fake_llm):
    first = client.post("/api/chat", json={"message": "Tell me about the AI and ML community curriculum"}).json()
    sid = first["session_id"]
    r = client.post("/api/chat", json={"message": "Who mentors it?", "session_id": sid})
    assert r.status_code == 200
    assert any(c["kind"] == "condense" for c in fake_llm.calls), "follow-up must be rewritten before retrieval"
    logged = next(x for x in db.recent_interactions() if x["session_id"] == sid and x["question"] == "Who mentors it?")
    assert logged["standalone"] != "Who mentors it?"
    assert "AI and ML" in logged["standalone"]


# ---------------------------------------------------------------- Search
def test_TC04_search_returns_all_matching_members(client, fake_llm):
    r = client.post("/api/search", json={"query": "Intermediate AI and ML members in Pune"})
    assert r.status_code == 200
    body = r.json()
    f = body["understood"]
    assert (f["entity_type"], f["domain"], f["level"], f["chapter"]) == ("member", "AI and ML", "Intermediate", "Pune")
    truth = {m["id"] for m in community.members()
             if (m["domain"], m["level"], m["chapter"]) == ("AI and ML", "Intermediate", "Pune")}
    got = {x["id"] for x in body["results"]}
    assert got == truth
    assert all(x["why"] for x in body["results"]), "every result states why it matched"


def test_TC05_search_filters_parsed_and_ui_override(client, fake_llm):
    r = client.post("/api/search", json={"query": "beginner pentest workshops in Pune"})
    f = r.json()["understood"]
    assert (f["entity_type"], f["domain"], f["level"], f["chapter"]) == ("event", "Cybersecurity", "Beginner", "Pune")
    assert f["parser"] == "rules"

    r = client.post("/api/search", json={"query": "beginner pentest workshops in Pune", "level": "Intermediate"})
    body = r.json()
    assert body["understood"]["level"] == "Intermediate", "interface filter overrides the parsed level"
    for x in body["results"]:
        assert x["type"] == "event"
        assert "Level: Intermediate" in x["why"] and "Chapter: Pune" in x["why"]


def test_TC06_search_llm_values_outside_vocabulary_discarded(client, fake_llm):
    fake_llm.search_reply = {"entity_type": "event", "domain": "Quantum Basket Weaving", "chapter": "Mars",
                             "level": "Godlike", "upcoming": False, "semantic_query": "robots"}
    r = client.post("/api/search", json={"query": "stuff happening for robot folks"})
    assert r.status_code == 200
    f = r.json()["understood"]
    assert f["parser"] == "llm"
    assert f["entity_type"] == "event"  # valid value kept
    assert f["domain"] is None and f["chapter"] is None and f["level"] is None  # invented values dropped


# ---------------------------------------------------------------- Recommendation
def _member_with_events():
    return community.members()[0]["id"]


def test_TC07_recommendations_for_valid_member(client, fake_llm):
    r = client.get(f"/api/recommendations/{_member_with_events()}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["peers"]) == 5
    assert len(body["events"]) <= 5
    assert all(e["score"] >= 2.5 for e in body["events"])
    for item in body["peers"] + body["events"] + body["modules"]:
        assert item["evidence"] and item["explanation"]
        assert not item["explanation"].startswith("Suggested because")


def test_TC08_recommendation_explanation_fallback_when_llm_down(client, fake_llm):
    fake_llm.fail_on.add("explain")
    r = client.get(f"/api/recommendations/{_member_with_events()}")
    assert r.status_code == 200
    for item in r.json()["peers"]:
        assert item["explanation"].startswith("Suggested because: ")


# ---------------------------------------------------------------- Member tools
def test_TC09_learning_path_grounded_in_curriculum(client, fake_llm):
    r = client.post("/api/learning-path", json={"goal": "Become an ML engineer", "current_skills": ["Python"],
                                                "domain": "AI and ML"})
    assert r.status_code == 200
    body = r.json()
    orders = [s["order"] for s in body["steps"]]
    assert orders == sorted(orders) and len(orders) >= 1
    path_call = next(c for c in fake_llm.calls if c["kind"] == "path")
    assert "TRACK: AI and ML" in path_call["user"] and "ALREADY KNOWS: Python" in path_call["user"]
    assert "(nothing found)" not in path_call["user"], "the prompt must carry retrieved curriculum text"


def test_TC10_resume_too_large_and_unreadable_image(client, fake_llm):
    big = b"a" * 5_000_001
    r = client.post("/api/resume", files={"file": ("cv.txt", big, "text/plain")})
    assert r.status_code == 413
    png = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4
    r = client.post("/api/resume", files={"file": ("cv.png", png, "image/png")})
    assert r.status_code == 422


def test_TC11_quiz_five_valid_mcqs(client, fake_llm):
    r = client.post("/api/quiz", json={"domain": "Cybersecurity", "level": "Beginner", "count": 5})
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 5
    for q in qs:
        assert len(q["options"]) == 4 and 0 <= q["answer_index"] < 4 and q["explanation"]


# ---------------------------------------------------------------- Admin
def test_TC12_admin_endpoint_without_token(client):
    assert client.get("/api/admin/unanswered").status_code == 401
    assert client.get("/api/admin/insights", headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_TC13_admin_answer_is_indexed_and_reused(client, fake_llm):
    q = "What is the refund policy for hostel mess charges?"
    first = client.post("/api/chat", json={"message": q}).json()
    assert first["answered"] is False
    item = next(x for x in client.get("/api/admin/unanswered", headers=ADMIN).json() if x["question"] == q)

    answer = "Hostel mess charges are refunded in full if you cancel at least seven days before the programme starts."
    r = client.post(f"/api/admin/unanswered/{item['id']}/answer", json={"answer": answer}, headers=ADMIN)
    assert r.status_code == 200
    assert vectorstore.get_by_ids([f"faq-{item['id']}"]), "the answer is indexed as an FAQ chunk"

    again = client.post("/api/chat", json={"message": q}).json()
    assert again["answered"] is True
    assert any(s["title"] == "ISDIC team answer" for s in again["sources"])


def test_TC14_insights_overview(client, fake_llm):
    for m in ["What does the Cloud & DevOps track cover?", "What does the cloud and devops curriculum include?",
              "What is the capital of France?"]:
        client.post("/api/chat", json={"message": m})
    r = client.get("/api/admin/insights", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["total_questions"] >= 3
    assert body["top_topics"] and body["knowledge_gaps"]
    assert {d["domain"] for d in body["domain_demand"]} == set(community.DOMAINS)
    for section in ("What members are asking", "Knowledge gaps", "Suggested actions"):
        assert section in body["narrative"]


# ---------------------------------------------------------------- LLM layer
def test_TC15_llm_endpoint_unreachable_returns_503(client, monkeypatch):
    from openai import OpenAI

    dead = OpenAI(base_url="http://127.0.0.1:9/v1", api_key="x", timeout=2, max_retries=0)
    monkeypatch.setattr(llm, "_get_client", lambda *a, **k: dead)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)  # skip the back-off waits
    monkeypatch.setattr(config, "LLM_MIN_INTERVAL", 0.0)
    r = client.post("/api/quiz", json={"domain": "Cybersecurity", "level": "Beginner", "count": 5})
    assert r.status_code == 503, r.text
    assert "unreachable" in r.json()["detail"]


# ---------------------------------------------------------------- Ingestion
def test_TC16_building_the_knowledge_base_twice_is_idempotent():
    from scripts import build_kb

    if not config.RAW_PAGES.exists():
        pytest.skip("no scraped pages (run scripts.scrape once)")
    build_kb.main()
    first = vectorstore.collection().count()
    ids_first = set(vectorstore.collection().get()["ids"])
    build_kb.main()
    assert vectorstore.collection().count() == first
    assert set(vectorstore.collection().get()["ids"]) == ids_first
    pages = [json.loads(l) for l in config.RAW_PAGES.read_text("utf-8").splitlines() if l.strip()]
    assert len(pages) > 0
