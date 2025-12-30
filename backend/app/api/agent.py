from __future__ import annotations

import inspect
import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import anyio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.mcp.tools import recipe_rag_query as mcp_recipe_rag_query
from app.rag.llm import stream_answer
from app.rag.retrieval import VectorStoreNotReadyError

router = APIRouter(prefix="/agent", tags=["agent"])


class Constraints(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20, description="How many chunks to retrieve.")


class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    constraints: Constraints = Field(default_factory=Constraints)


def _ndjson(event: str, data: Dict[str, Any]) -> str:
    # Streamable HTTP format: one JSON object per line (NDJSON).
    return json.dumps({"event": event, "data": data}, ensure_ascii=False) + "\n"


async def _call_recipe_tool(query: str, top_k: int) -> Dict[str, Any]:
    """
    Call the cookbook RAG tool (sync or async) without blocking the event loop.
    """
    def _sync_call() -> Any:
        return mcp_recipe_rag_query(query=query, constraints={"top_k": top_k})

    res = await anyio.to_thread.run_sync(_sync_call)
    if inspect.isawaitable(res):
        res = await res
    if not isinstance(res, dict):
        raise TypeError(f"recipe_rag_query_tool returned {type(res).__name__}, expected dict")
    return res


@router.post("/run")
async def run_agent(req: AgentRunRequest):
    """
    Stream agent events as NDJSON (Streamable HTTP).
    """

    async def gen() -> AsyncGenerator[str, None]:
        run_id = str(uuid.uuid4())
        t0 = time.monotonic()

        try:
            yield _ndjson("run.started", {"run_id": run_id, "ts": time.time()})
            yield _ndjson(
                "plan.created",
                {
                    "run_id": run_id,
                    "plan": "1) Retrieve grounded cookbook evidence. 2) Answer using only that evidence with citations.",
                },
            )

            top_k = int(req.constraints.top_k)

            yield _ndjson(
                "tool.call.started",
                {
                    "run_id": run_id,
                    "tool": "recipe_rag_query",
                    "query": req.message,
                    "constraints": {"top_k": top_k},
                },
            )

            tool_res = await _call_recipe_tool(req.message, top_k)
            chunks = tool_res.get("chunks", []) or []
            citations = tool_res.get("citations", []) or []

            tool_latency_s: Optional[float] = None
            if tool_res.get("latency_ms") is not None:
                tool_latency_s = round(float(tool_res["latency_ms"]) / 1000.0, 3)

            yield _ndjson(
                "tool.call.finished",
                {
                    "run_id": run_id,
                    "tool": "recipe_rag_query",
                    "latency_s": tool_latency_s,
                    "chunks_count": len(chunks),
                },
            )

            # (a) no-evidence guardrail (fast path: skip LLM)
            if len(chunks) == 0:
                answer = "I can’t find that in this cookbook."
                yield _ndjson(
                    "answer.generated",
                    {
                        "run_id": run_id,
                        "answer": answer,
                        "citations": [],
                        "reason": "no_evidence",
                    },
                )
                total_s = round(time.monotonic() - t0, 3)
                yield _ndjson("run.finished", {"run_id": run_id, "total_latency_s": total_s})
                return

            # LLM streaming (tokens)
            answer_text = ""
            llm_t0 = time.monotonic()
            async for token in stream_answer(req.message, chunks, history=[]):
                if token:
                    answer_text += token
                    yield _ndjson("answer.token", {"run_id": run_id, "token": token})

            llm_latency_s = round(time.monotonic() - llm_t0, 3)
            yield _ndjson(
                "answer.generated",
                {
                    "run_id": run_id,
                    "answer": answer_text.strip(),
                    "citations": citations,
                    "llm_latency_s": llm_latency_s,
                },
            )

            total_s = round(time.monotonic() - t0, 3)
            yield _ndjson("run.finished", {"run_id": run_id, "total_latency_s": total_s})

        except VectorStoreNotReadyError as e:
            yield _ndjson("run.error", {"run_id": run_id, "error": str(e)})
        except Exception as e:
            yield _ndjson("run.error", {"run_id": run_id, "error": f"{type(e).__name__}: {e}"})

    return StreamingResponse(gen(), media_type="application/x-ndjson; charset=utf-8")
