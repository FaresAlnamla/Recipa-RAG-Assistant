from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RAGQueryConstraints(BaseModel):
    """
    Optional constraints for retrieval.

    Notes:
    - Your current retriever only supports k directly (retrieve_docs(question, k)).
    - The remaining constraints are applied as post-filters on retrieved docs.
    """
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to return.")
    source_contains: Optional[str] = Field(
        default=None,
        description="Keep only chunks whose source string contains this substring (case-insensitive).",
    )
    page_min: Optional[int] = Field(default=None, ge=0, description="Minimum page (inclusive).")
    page_max: Optional[int] = Field(default=None, ge=0, description="Maximum page (inclusive).")

    @classmethod
    def from_constraints_dict(cls, constraints: Optional[Dict[str, Any]]) -> "RAGQueryConstraints":
        if not constraints:
            return cls()
        # Ignore unknown keys safely (best practice for agent-facing tools)
        allowed = {"top_k", "source_contains", "page_min", "page_max"}
        cleaned = {k: v for k, v in constraints.items() if k in allowed}
        return cls(**cleaned)


class Chunk(BaseModel):
    text: str
    source: str
    page: Optional[int] = None
    chunk_id: str


class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    chunk_id: str


class RecipeRAGQueryResponse(BaseModel):
    chunks: List[Chunk] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    latency_ms: int = Field(..., ge=0)
