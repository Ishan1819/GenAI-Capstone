import uuid

from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest
from app.database import vectorstore
from app.rag import chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/health")
def health():
    return {"status": "ok", "chunks": vectorstore.collection().count()}


@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    try:
        return {"session_id": sid, **chat.answer(sid, req.message)}
    except RuntimeError as e:
        raise HTTPException(503, str(e))
