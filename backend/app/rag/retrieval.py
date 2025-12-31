from __future__ import annotations

import re
from functools import lru_cache
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings

_settings = get_settings()


class VectorStoreNotReadyError(RuntimeError):
    pass


# Stopwords for keyword guardrail
_STOPWORDS = {
    "how", "do", "i", "make", "cook", "recipe", "a", "an", "the", "for", "to", "of",
    "in", "on", "with", "and", "or", "please", "give", "me", "steps", "step", "by",
    "it", "this", "that", "is", "are", "can", "you", "tell", "what", "when",
}


def _extract_keywords(question: str) -> List[str]:
    """Extract meaningful keywords from a question for guardrail checks."""
    tokens = re.findall(r"[a-zA-Z]{3,}", (question or "").lower())
    kws = [t for t in tokens if t not in _STOPWORDS]
    
    # De-dup preserving order
    seen = set()
    out = []
    for t in kws:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _keyword_guardrail(question: str, docs: List[Document]) -> bool:
    """
    Check if retrieved docs contain at least one meaningful keyword from the query.
    This prevents irrelevant top_k chunks from being treated as evidence.
    """
    kws = _extract_keywords(question)
    if not kws:
        return True  # nothing to check

    ctx = " ".join((d.page_content or "") for d in docs).lower()
    return any(k in ctx for k in kws)


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    """
    Build the Chroma vector store once and cache it in-memory.
    Subsequent requests reuse the same instance.
    """
    embeddings = OpenAIEmbeddings(
        model=_settings.embedding_model,
        api_key=_settings.openai_api_key,
    )
    
    return Chroma(
        embedding_function=embeddings,
        persist_directory=str(_settings.vectorstore_dir),
        collection_name=_settings.chroma_collection,
    )


def get_vectorstore() -> Chroma:
    """
    Get the Chroma vector store instance (cached).
    """
    return _get_vectorstore()


def get_retriever(k: int = 5):
    """
    Return a retriever instance from the vectorstore.
    """
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(search_kwargs={"k": k})


def retrieve_docs(question: str, k: int = 5) -> List[Document]:
    """
    Retrieve documents for a question.
    
    Args:
        question: The user's question
        k: Number of documents to retrieve
    
    Returns:
        List of Document objects from the cookbook
    
    Raises:
        VectorStoreNotReadyError: If vectorstore is not initialized
    """
    try:
        vectorstore = get_vectorstore()
        docs = vectorstore.similarity_search(question, k=k)
        return docs
    except Exception as e:
        raise VectorStoreNotReadyError(f"Failed to retrieve documents: {str(e)}")
