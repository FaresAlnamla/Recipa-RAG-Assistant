from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.config import VECTORSTORE_DIR, get_settings

_settings = get_settings()


class VectorStoreNotReadyError(RuntimeError):
    """Raised when the Chroma vector store has not been built yet."""


# -----------------------------
# (b) Query-embedding cache
# -----------------------------
class CachedEmbeddings(Embeddings):
    """
    Wraps an embeddings provider and caches embed_query() results.
    This avoids paying the embeddings API call repeatedly for identical queries.
    """

    def __init__(self, base: Embeddings, maxsize: int = 1024):
        self._base = base

        @lru_cache(maxsize=maxsize)
        def _cached_embed_query(text: str) -> Tuple[float, ...]:
            vec = self._base.embed_query(text)
            return tuple(vec)

        self._cached_embed_query = _cached_embed_query

    def embed_query(self, text: str) -> List[float]:
        key = (text or "").strip()
        return list(self._cached_embed_query(key))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Ingestion uses embed_documents; caching it is optional.
        return self._base.embed_documents(texts)


_QUERY_CACHE_SIZE = int(os.getenv("QUERY_EMBED_CACHE_SIZE", "2048"))

_embeddings = CachedEmbeddings(
    OpenAIEmbeddings(
        api_key=_settings.openai_api_key,
        model=_settings.embedding_model,
    ),
    maxsize=_QUERY_CACHE_SIZE,
)


# -----------------------------
# Vectorstore loader
# -----------------------------
@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    # Basic “is it built?” check
    if not VECTORSTORE_DIR.exists():
        raise VectorStoreNotReadyError(
            f"Vectorstore directory not found: {VECTORSTORE_DIR}. "
            "Run ingestion to build it."
        )

    # Common Chroma persistence file
    sqlite_path = VECTORSTORE_DIR / "chroma.sqlite3"
    if not sqlite_path.exists():
        # Still allow alternate persistence layouts, but warn with clear error
        raise VectorStoreNotReadyError(
            f"Chroma persistence file not found: {sqlite_path}. "
            "Run ingestion to build it."
        )

    return Chroma(
        embedding_function=_embeddings,
        persist_directory=str(VECTORSTORE_DIR),
        collection_name=_settings.chroma_collection,
    )


# -----------------------------
# (a) No-evidence guardrail
# -----------------------------
_STOPWORDS = {
    "how", "do", "i", "make", "cook", "recipe", "a", "an", "the", "for", "to", "of",
    "in", "on", "with", "and", "or", "please", "give", "me", "steps", "step", "by",
    "it", "this", "that", "is", "are", "can", "you", "tell", "what", "when",
}

def _extract_keywords(question: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", (question or "").lower())
    kws = [t for t in tokens if t not in _STOPWORDS]
    # de-dup preserving order
    seen = set()
    out = []
    for t in kws:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _keyword_guardrail(question: str, docs: List[Document]) -> bool:
    """
    Returns True if retrieved docs contain at least one meaningful keyword from the query.
    This prevents irrelevant top_k chunks from being treated as evidence.
    """
    kws = _extract_keywords(question)
    if not kws:
        return True  # nothing to check

    ctx = " ".join((d.page_content or "") for d in docs).lower()
    return any(k in ctx for k in kws)


def retrieve_docs(
    question: str,
    k: int = 5,
    *,
    min_relevance: Optional[float] = None,
) -> List[Document]:
    """
    Retrieves documents for a question.

    Guardrails:
    - Optional relevance-score filtering (if supported by the vectorstore)
    - Keyword guardrail: if none of the query’s keywords appear in retrieved text, return []
      (prevents irrelevant citations for out-of-scope questions)
    """
    vectorstore = _get_vectorstore()

    # 1) Try score-aware retrieval if threshold provided (optional)
    docs: List[Document] = []
    if min_relevance is not None:
        try:
            pairs = vectorstore.similarity_search_with_relevance_scores(question, k=k)
            for doc, score in pairs:
                doc.metadata = (doc.metadata or {})
                doc.metadata["relevance"] = float(score)
                if float(score) >= float(min_relevance):
                    docs.append(doc)
        except Exception:
            # Fallback: no score API; do plain retrieval
            docs = vectorstore.similarity_search(question, k=k)
    else:
        docs = vectorstore.similarity_search(question, k=k)

    # 2) Keyword guardrail (high impact for “pancakes” case)
    if not _keyword_guardrail(question, docs):
        return []

    return docs
