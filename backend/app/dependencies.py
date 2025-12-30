from app.rag.retrieval import get_retriever
from app.rag.llm import get_llm_chain


def get_retriever_dep():
    return get_retriever(k=5)


def get_llm_chain_dep():
    return get_llm_chain()