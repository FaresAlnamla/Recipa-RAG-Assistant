from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import settings


class VectorStoreNotReadyError(RuntimeError):
    pass


class CachedOpenAIEmbeddings(OpenAIEmbeddings):
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


def retrieve_docs(query: str, *, top_k: int = 5) -> List[Document]:
    vs = _get_vectorstore()
    retriever = vs.as_retriever(search_kwargs={"k": int(top_k)})
    return retriever.get_relevant_documents(query)
