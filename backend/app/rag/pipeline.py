from typing import Any, Dict, List
from langchain_core.documents import Document

MAX_SNIPPET_CHARS = 300
MAX_CONTEXT_CHARS = 8000

def build_sources(docs: List[Document]) -> List[Dict[str, Any]]:
    out = []
    for d in docs:
        md = d.metadata or {}
        out.append({
            "page": md.get("page"),
            "page_label": md.get("page_label"),
            "source": md.get("source"),
            "snippet": (d.page_content or "")[:MAX_SNIPPET_CHARS],
        })
    return out

def build_context(docs: List[Document]) -> str:
    parts = []
    for d in docs:
        md = d.metadata or {}
        # نفضّل page_label لأنه أوضح للمستخدم
        page_label = md.get("page_label")
        header = f"[page={page_label}]" if page_label else "[page=?]"
        parts.append(f"{header}\n{d.page_content}")
    ctx = "\n\n---\n\n".join(parts)
    return ctx[:MAX_CONTEXT_CHARS]

def run_rag(question: str, retriever, llm_chain) -> Dict[str, Any]:
    docs: List[Document] = retriever.invoke(question)

    context = build_context(docs)
    sources = build_sources(docs)

    result = llm_chain.invoke({"question": question, "context": context})
    answer_text = getattr(result, "content", result)

    return {"answer": answer_text, "sources": sources}
