from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from langchain_core.documents import Document
except Exception:
    Document = Any

from app.rag.retrieval import get_vectorstore


@dataclass
class RetrievedChunk:
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


def retrieve_cookbook(query: str, k: int = 4) -> List[RetrievedChunk]:
    query = (query or "").strip()
    if not query:
        return []

    vs = get_vectorstore()

    try:
        results = vs.similarity_search_with_score(query, k=k)
        chunks: List[RetrievedChunk] = []
        for doc, score in results:
            chunks.append(
                RetrievedChunk(
                    content=getattr(doc, "page_content", str(doc)),
                    metadata=getattr(doc, "metadata", {}) or {},
                    score=float(score) if score is not None else None,
                )
            )
        return chunks
    except Exception:
        docs = vs.similarity_search(query, k=k)
        return [
            RetrievedChunk(
                content=getattr(doc, "page_content", str(doc)),
                metadata=getattr(doc, "metadata", {}) or {},
                score=None,
            )
            for doc in docs
        ]
