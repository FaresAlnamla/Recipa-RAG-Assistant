from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.agent import answer_with_agent, answer_with_agent_stream
from app.agent.memory import clear_session, get_history

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentAskRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"


class SourceItem(BaseModel):
    page: Optional[int] = None
    page_label: Optional[str] = None
    source: Optional[str] = None
    book_name: Optional[str] = None  # ✅ NEW: Friendly book name for display
    snippet: str = ""


class EvaluationItem(BaseModel):
    supported: bool = False
    confidence: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    facts_checked: List[str] = Field(default_factory=list)


class AgentAskResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
    evaluation: EvaluationItem = Field(default_factory=EvaluationItem)
    filtered_out: List[dict] = Field(default_factory=list)


@router.post("/ask", response_model=AgentAskResponse)
def agent_ask(payload: AgentAskRequest) -> AgentAskResponse:
    result = answer_with_agent(payload.question, session_id=payload.session_id)

    # ✅ Normalize missing keys so pydantic doesn't break
    result.setdefault("sources", [])
    result.setdefault("filtered_out", [])
    result.setdefault(
        "evaluation",
        {"supported": False, "confidence": 0.0, "reasons": ["missing_eval"], "facts_checked": []},
    )

    return AgentAskResponse(**result)


@router.post("/ask/stream")
def agent_ask_stream(payload: AgentAskRequest):
    session_id = (payload.session_id or "default").strip()

    def event_gen():
        # ✅ optional: send meta first (helps frontend know session_id)
        meta_evt = {"type": "meta", "session_id": session_id}
        yield f"data: {json.dumps(meta_evt, ensure_ascii=False)}\n\n"

        for evt in answer_with_agent_stream(payload.question, session_id=session_id):
            # ✅ ensure evt is JSON-safe
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    headers = {
        # SSE best practices:
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # If you're behind nginx, this helps prevent buffering:
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)


class ClearMemoryRequest(BaseModel):
    session_id: str


@router.post("/memory/clear")
def agent_clear_memory(payload: ClearMemoryRequest):
    clear_session(payload.session_id)
    return {"ok": True}


# ✅ (اختياري لكن مفيد جدًا للاختبار) قراءة history
class HistoryResponseItem(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    history: List[HistoryResponseItem]


@router.get("/memory/history", response_model=HistoryResponse)
def agent_get_history(session_id: str = "default", limit: int = 10):
    hist = get_history(session_id, limit=limit)
    return {"session_id": session_id, "history": hist}
