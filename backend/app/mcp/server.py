from __future__ import annotations

from fastmcp import FastMCP

# IMPORTANT: import the tool from .tools (NOT from app.mcp.server)
from .tools import recipe_rag_query

mcp = FastMCP("Recipa RAG Tools")

# Expose tool
mcp.tool()(recipe_rag_query)

# Streamable HTTP transport
# This ASGI app will be mounted under /mcp in FastAPI, so path="/"
app = mcp.http_app(path="/")
