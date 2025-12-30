from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.config import VECTORSTORE_DIR, get_settings

_settings = get_settings()


class VectorStoreNotReadyError(RuntimeError):
    """Raised when the Chroma vector store has not been built yet."""
    pass


def _ensure_vectorstore_ready() -> None:
    """
    Check if the vectorstore directory exists and is non-empty.
    If not, raise a clear error telling the user to run ingestion.
    """
    path = Path(VECTORSTORE_DIR)
    if not path.exists() or not any(path.iterdir()):
        raise VectorStoreNotReadyError(
            "Vector store is empty or missing. "
            "Run `python -m scripts.run_ingest` from the backend/ folder first."
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

    return Chroma(
        embedding_function=embeddings,
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
    return docs
