from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .tools import recipe_rag_query

mcp = FastMCP(
    name="recipaai-mcp",
    instructions="Exposes RecipaAI retrieval as MCP tools. Return only grounded evidence.",
)

@mcp.tool(
    name="recipe_rag_query",
    description="Retrieve grounded cookbook chunks for a query. Returns chunks, citations, latency_ms.",
)
def recipe_rag_query_tool(
    query: str,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return recipe_rag_query(query=query, constraints=constraints).model_dump()

# Serve SSE transport (Inspector-friendly)
# This app exposes:
#   GET  /sse
#   POST /message
app = mcp.sse_app()
