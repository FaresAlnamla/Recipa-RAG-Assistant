from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app.rag.retrieval import retrieve_docs, VectorStoreNotReadyError  # your existing retrieval :contentReference[oaicite:3]{index=3}
from .schemas import Chunk, Citation, RAGQueryConstraints, RecipeRAGQueryResponse


def _safe_source(doc: Document) -> str:
    meta = getattr(doc, "metadata", {}) or {}
    src = str(meta.get("source") or meta.get("file_path") or "").strip()
    if src:
        return Path(src).name  # -> "COOKBOOK.pdf"
    return "COOKBOOK.pdf"


def _safe_page(doc: Document) -> Optional[int]:
    meta = getattr(doc, "metadata", {}) or {}
    page = meta.get("page", None)
    if page is None:
        return None
    try:
        return int(page)
    except Exception:
        return None


def _make_chunk_id(source: str, page: Optional[int], text: str) -> str:
    """
    Deterministic chunk id. Uses only data we actually have.
    """
    key = f"{source}|{page}|{text[:120]}".encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()[:16]


def _apply_post_filters(
    docs: List[Document],
    constraints: RAGQueryConstraints,
) -> List[Document]:
    """
    Apply optional constraints as post-filters after retrieval.
    """
    out: List[Document] = []

    src_sub = constraints.source_contains.lower().strip() if constraints.source_contains else None
    pmin = constraints.page_min
    pmax = constraints.page_max

    for d in docs:
        src = _safe_source(d)
        page = _safe_page(d)

        if src_sub and src_sub not in src.lower():
            continue
        if page is not None:
            if pmin is not None and page < pmin:
                continue
            if pmax is not None and page > pmax:
                continue

        out.append(d)

    return out


def recipe_rag_query(
    query: str,
    constraints: Optional[Dict[str, Any]] = None,
) -> RecipeRAGQueryResponse:
    """
    MCP Tool: recipe_rag_query(query, constraints?) -> {chunks, citations, latency_ms}

    Hard rules enforced:
    - citations match chunks 1:1
    - no hallucinated sources (only doc metadata or safe fallback label)
    - if no evidence -> chunks=[], citations=[]
    """
    t0 = time.monotonic()
    query = (query or "").strip()

    # If query is empty, return empty evidence (no guessing).
    if not query:
        return RecipeRAGQueryResponse(chunks=[], citations=[], latency_ms=0)

    c = RAGQueryConstraints.from_constraints_dict(constraints)

    try:
        # Retrieve more than needed if we plan to post-filter.
        # Simple heuristic: retrieve 2x top_k to avoid filtering down to nothing.
        raw_k = min(max(c.top_k * 2, c.top_k), 20)
        docs = retrieve_docs(query, k=raw_k)  # your retrieval entrypoint :contentReference[oaicite:4]{index=4}
    except VectorStoreNotReadyError:
        # If vectorstore missing, do NOT fabricate evidence.
        latency_ms = int((time.monotonic() - t0) * 1000)
        return RecipeRAGQueryResponse(chunks=[], citations=[], latency_ms=latency_ms)

    filtered = _apply_post_filters(docs, c)

    # Take final top_k after filtering
    final_docs = filtered[: c.top_k]

    chunks: List[Chunk] = []
    citations: List[Citation] = []

    for d in final_docs:
        text = (getattr(d, "page_content", "") or "").strip()
        if not text:
            continue

        source = _safe_source(d)
        page = _safe_page(d)
        chunk_id = _make_chunk_id(source, page, text)

        chunks.append(
            Chunk(
                text=text,
                source=source,
                page=page,
                chunk_id=chunk_id,
            )
        )
        citations.append(
            Citation(
                source=source,
                page=page,
                chunk_id=chunk_id,
            )
        )

    latency_ms = int((time.monotonic() - t0) * 1000)
    return RecipeRAGQueryResponse(chunks=chunks, citations=citations, latency_ms=latency_ms)
