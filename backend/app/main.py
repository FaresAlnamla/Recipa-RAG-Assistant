import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.mcp.server import app as mcp_asgi_app

logger = logging.getLogger("uvicorn")

app = FastAPI(title="RecipaAI API (MCP + Agent)")

# Routers
app.include_router(agent_router)

# Mount MCP inside the same FastAPI service
# Effective endpoints:
#   GET  /mcp/sse
#   POST /mcp/message
app.mount("/mcp", mcp_asgi_app)

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

@app.get("/health")
def health():
    return {"status": "ok"}
