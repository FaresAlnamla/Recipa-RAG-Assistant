from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.mcp.server import app as mcp_asgi_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mounted apps don't automatically run their lifespans; proxy FastMCP lifespan here.
    if getattr(mcp_asgi_app, "lifespan", None):
        async with mcp_asgi_app.lifespan(app):
            yield
    else:
        yield


app = FastAPI(title="Recipa RAG Assistant", version="1.0.0", lifespan=lifespan)

# CORS (frontend: local + Vercel)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://recipaai.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# MCP served under /mcp
app.mount("/mcp", mcp_asgi_app)
