from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import re
from functools import lru_cache
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import settings


class VectorStoreNotReadyError(RuntimeError):
    pass


class CachedOpenAIEmbeddings(OpenAIEmbeddings):
def _ensure_vectorstore_ready() -> None:
# -----------------------------
# (b) Query-embedding cache
# -----------------------------
class CachedEmbeddings(Embeddings):
    """
    In-process LRU cache for query embeddings.
    - Speeds up repeated queries (same text).
    - Cache is per-process (resets on restart).
    """

    @lru_cache(maxsize=2048)
    def _cached_query(self, text: str) -> Tuple[float, ...]:
        return tuple(super().embed_query(text))

    def embed_query(self, text: str) -> List[float]:
        return list(self._cached_query(text))


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    if not settings.CHROMA_PERSIST_DIR:
        raise VectorStoreNotReadyError("CHROMA_PERSIST_DIR is not set.")
    embeddings = CachedOpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    return Chroma(persist_directory=settings.CHROMA_PERSIST_DIR, embedding_function=embeddings)
    # Basic “is it built?” check
    if not VECTORSTORE_DIR.exists():
        raise VectorStoreNotReadyError(
            f"Vectorstore directory not found: {VECTORSTORE_DIR}. "
            "Run ingestion to build it."
        )


@lru_cache
def get_vectorstore() -> Chroma:
    """
    Build the Chroma vector store once and cache it in-memory.
    Subsequent requests reuse the same instance.
    """
    _ensure_vectorstore_ready()

    embeddings = OpenAIEmbeddings(
        model=_settings.embedding_model,
        api_key=_settings.openai_api_key,
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


# -------------------------------------------------------------------
# Backward-compatible alias (some parts of the app still import this)
# Keep it until you refactor all imports to use get_vectorstore().
# -------------------------------------------------------------------
def _get_vectorstore() -> Chroma:
    return get_vectorstore()


def get_retriever(k: int = 5):
    """
    Return a retriever instance from the vectorstore.
    """
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(search_kwargs={"k": k})


def retrieve_docs(question: str, k: int = 5) -> List[Document]:
    """
    Convenience function: build retriever and retrieve docs for a question.
    Uses `invoke()` to align with LangChain runnable interfaces.
    """
    retriever = get_retriever(k=k)
    docs: List[Document] = retriever.invoke(question)
    return docs


def retrieve(retriever, question: str, k: Optional[int] = None) -> List[Document]:
    """
    Retrieve docs using an already constructed retriever.
    If k is provided, it overrides retriever search kwargs (best-effort).
    """
    if k is not None and hasattr(retriever, "search_kwargs"):
        retriever.search_kwargs = {**getattr(retriever, "search_kwargs", {}), "k": k}

    docs: List[Document] = retriever.invoke(question)
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


def retrieve_docs(query: str, *, top_k: int = 5) -> List[Document]:
    vs = _get_vectorstore()
    retriever = vs.as_retriever(search_kwargs={"k": int(top_k)})
    return retriever.get_relevant_documents(query)
