"""Admin-only endpoints (ISDIC team and chapter leads). Every route needs the X-Admin-Token header."""
from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.schemas import AnswerRequest, SessionPlanRequest
from app.core import config
from app.database import db
from app.services import admin, session_plan


def require_admin(x_admin_token: str = Header(default="")):
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/verify")
def verify():
    return {"ok": True}


@router.get("/unanswered")
def list_unanswered(status: str = "open"):
    return db.list_unanswered(status)


@router.post("/unanswered/{item_id}/answer")
def answer_unanswered(item_id: int, req: AnswerRequest):
    try:
        admin.resolve_with_answer(item_id, req.answer)
    except KeyError:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/unanswered/{item_id}/dismiss")
def dismiss_unanswered(item_id: int):
    db.resolve_unanswered(item_id, "dismissed")
    return {"ok": True}


@router.get("/insights")
def insights(narrative: bool = True):
    try:
        return admin.compute_insights(narrative)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/session-plan")
def session_plan_endpoint(req: SessionPlanRequest):
    try:
        return session_plan.generate_plan(req.domain, req.topic, req.level, req.duration_hours, req.format, req.notes)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


