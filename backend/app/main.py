from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.retrieval import retrieve_docs, VectorStoreNotReadyError
from app.rag.llm import stream_answer
from app.api.agent_routes import router as agent_router
from app.agent.memory import init_memory_db
from app.mcp.server import app as mcp_asgi_app

logger = logging.getLogger("uvicorn")


def warmup_vectorstore():
    """Initialize vectorstore on startup."""
    from app.rag.retrieval import get_vectorstore  # local import to avoid cycles
    try:
        get_vectorstore()
    except Exception as e:
        logging.getLogger("uvicorn").warning("Vectorstore warmup failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_memory_db()
    warmup_vectorstore()
    
    # Mounted apps don't automatically run their lifespans; proxy FastMCP lifespan here.
    if getattr(mcp_asgi_app, "lifespan", None):
        async with mcp_asgi_app.lifespan(app):
            yield
    else:
        yield


app = FastAPI(
    title="Recipa RAG Assistant",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Agent", "description": "Agent endpoints (cookbook grounded)"},
        {"name": "default", "description": "Base RAG endpoints"},
    ],
)

# CORS: Dynamic configuration based on environment
settings = get_settings()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    settings.frontend_url,
    "https://recipaai.vercel.app",
]

# Remove duplicates while preserving order
seen = set()
origins = [x for x in origins if not (x in seen or seen.add(x))]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)




class HistoryItem(BaseModel):
    question: str
    answer: str


class AskRequest(BaseModel):
    question: str
    k: int = 3
    history: List[HistoryItem] = Field(default_factory=list)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", tags=["default"])
def ask(req: AskRequest):
    """
    Single streaming endpoint.
    Returns a plain-text stream of tokens as they are generated.
    """
    t0 = time.monotonic()

    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "Server misconfigured: OPENAI_API_KEY is not set. "
                "Add it to backend/.env and restart the server."
            ),
        )

    try:
        # Retrieval happens once before streaming
        t1 = time.monotonic()
        docs = retrieve_docs(req.question, k=req.k)
        t2 = time.monotonic()

        history_payload = [{"question": h.question, "answer": h.answer} for h in req.history]

        def token_generator():
            t_llm_start = time.monotonic()
            for chunk in stream_answer(question=req.question, docs=docs, history=history_payload):
                yield chunk
            t_llm_end = time.monotonic()

            logger.info(
                "ASK(stream) timings: total=%.2fs, retrieve=%.2fs, llm=%.2fs",
                t_llm_end - t0,
                t2 - t1,
                t_llm_end - t_llm_start,
            )

        return StreamingResponse(token_generator(), media_type="text/plain")

    except VectorStoreNotReadyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# MCP served under /mcp
app.mount("/mcp", mcp_asgi_app)


# Allow Render and other platforms to bind to custom port
if __name__ == "__main__":
    import os
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0"  # Required for Render to bind correctly
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
