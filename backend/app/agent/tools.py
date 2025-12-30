from typing import Any, Dict, List, Optional
from app.rag.retrieval import retrieve_docs
from app.rag.llm import generate_answer

from .memory_store import add_fact, add_turn, get_recent_facts

def rag_tool(question: str, k: int, history: Optional[List[Dict[str, Any]]]) -> str:
    docs = retrieve_docs(question=question, k=k)
    return generate_answer(question=question, docs=docs, history=history)

def memory_read_tool() -> str:
    facts = get_recent_facts(limit=8)
    if not facts:
        return "No long-term memory yet."
    return "\n".join([f"- {x}" for x in facts])

def memory_write_tool(text: str, tag: str = "preference") -> str:
    add_fact(text, tag=tag)
    return "saved"

def log_turn_tool(user: str, assistant: str) -> str:
    add_turn(user, assistant)
    return "logged"
