from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional, AsyncGenerator, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from langchain_core.documents import Document

from app.mcp.server import recipe_rag_query_tool as mcp_recipe_rag_query
from app.rag.llm import stream_answer
from app.rag.retrieval import VectorStoreNotReadyError

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    constraints: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


def _sse(event: str, data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/run")
def agent_run(req: AgentRunRequest) -> StreamingResponse:
    run_id = str(uuid.uuid4())
    t0 = time.monotonic()

    async def gen() -> AsyncGenerator[str, None]:
        try:
            yield _sse("run.started", {"run_id": run_id, "ts": time.time()})

            plan = "1) Retrieve grounded cookbook evidence. 2) Answer using only that evidence with citations."
            yield _sse("plan.created", {"run_id": run_id, "plan": plan})

            constraints = req.constraints or {}

            yield _sse(
                "tool.call.started",
                {
                    "run_id": run_id,
                    "tool": "recipe_rag_query",
                    "query": req.message,
                    "constraints": constraints,
                },
            )

            t_tool = time.monotonic()
            tool_res = mcp_recipe_rag_query(query=req.message, constraints=constraints)  # dict
            tool_latency_ms = int((time.monotonic() - t_tool) * 1000)

            chunks = tool_res.get("chunks", []) or []
            citations = tool_res.get("citations", []) or []

            # Always emit tool.call.finished (even when chunks are empty)
            yield _sse(
                "tool.call.finished",
                {
                    "run_id": run_id,
                    "tool": "recipe_rag_query",
                    "latency_ms": tool_latency_ms,
                    "chunks_count": len(chunks),
                },
            )

            # No-evidence fast path: skip LLM entirely
            if not chunks:
                msg = "I can’t find that in this cookbook."
                yield _sse("answer.token", {"run_id": run_id, "token": msg})
                yield _sse(
                    "answer.generated",
                    {
                        "run_id": run_id,
                        "answer": msg,
                        "citations": [],
                        "llm_latency_ms": 0,
                        "reason": "no_evidence",
                    },
                )
                total_ms = int((time.monotonic() - t0) * 1000)
                yield _sse("run.finished", {"run_id": run_id, "total_latency_ms": total_ms})
                return

            # Build docs for LLM prompt
            docs: List[Document] = [
                Document(
                    page_content=(ch.get("text") or ""),
                    metadata={
                        "source": ch.get("source"),
                        "page": ch.get("page"),
                        "chunk_id": ch.get("chunk_id"),
                    },
                )
                for ch in chunks
            ]

            # Stream tokens
            answer_buf: list[str] = []
            t_llm = time.monotonic()

            for token in stream_answer(req.message, docs, history=req.history):
                answer_buf.append(token)
                yield _sse("answer.token", {"run_id": run_id, "token": token})

            answer_text = "".join(answer_buf)
            llm_latency_ms = int((time.monotonic() - t_llm) * 1000)

            yield _sse(
                "answer.generated",
                {
                    "run_id": run_id,
                    "answer": answer_text,
                    "citations": citations,
                    "llm_latency_ms": llm_latency_ms,
                },
            )

            total_ms = int((time.monotonic() - t0) * 1000)
            yield _sse("run.finished", {"run_id": run_id, "total_latency_ms": total_ms})

        except VectorStoreNotReadyError as e:
            yield _sse("run.error", {"run_id": run_id, "error": str(e)})
        except Exception as e:
            yield _sse("run.error", {"run_id": run_id, "error": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
