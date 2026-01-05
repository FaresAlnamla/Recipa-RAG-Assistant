from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re

from pydantic import BaseModel

from app.agent.eval import filter_and_rank_chunks
from app.agent.tools.retrieval_tool import RetrievedChunk, retrieve_cookbook


COOKING_KEYWORDS = {
    "recipe", "ingredients", "cook", "bake", "boil", "fry", "grill", "roast",
    "oven", "temperature", "degrees", "prep", "time", "serves", "yield",
    "cup", "tbsp", "tsp", "grams", "ml",
    "cheap", "budget", "affordable", "author", "authors", "book", "books",
    "meal", "family", "lentil", "lentils", "egg", "eggs", "flour",
    "taste", "good", "simple", "easy", "quick", "fast",
}

CATALOG_HINTS = {
    "list", "all", "index", "contents", "table of contents", "toc",
    "what recipes", "which recipes", "recipes are in this book", "recipe list",
    "chapters",
}


@dataclass
class RouteDecision:
    use_cookbook: bool
    reason: str


def _is_catalog_intent(user_query: str) -> bool:
    q = (user_query or "").strip().lower()
    if not q:
        return False
    if any(h in q for h in CATALOG_HINTS):
        return True
    if "list of recipes" in q or ("recipes" in q and ("list" in q or "all" in q or "index" in q or "contents" in q)):
        return True
    return False


def decide_route(user_query: str) -> RouteDecision:
    q = (user_query or "").strip().lower()
    if not q:
        return RouteDecision(False, "Empty question.")

    if _is_catalog_intent(q):
        return RouteDecision(True, "Catalog/TOC intent detected.")

    if any(k in q for k in COOKING_KEYWORDS):
        return RouteDecision(True, "Cooking intent detected.")

    food_hints = ["cake", "cookies", "muffin", "egg", "chicken", "rice", "salad", "soup", "pasta", "tuna", "tofu", "pepper"]
    # include common single-word ingredient hints and low-cost indicators
    extended_hints = food_hints + ["lentil", "lentils", "egg", "eggs", "flour", "cheap", "budget", "meal", "family"]
    if any(w in q for w in extended_hints):
        return RouteDecision(True, "Food-related intent detected.")

    # Check for questions about the book itself (author, publication, etc.)
    book_questions = ["author", "write", "published", "publication", "who wrote", "who is the author"]
    if any(bq in q for bq in book_questions):
        return RouteDecision(True, "Book metadata question detected.")

    return RouteDecision(False, "Out of cookbook scope.")


def _looks_like_toc_or_index(text: str) -> bool:
    t = (text or "").lower()
    if not t:
        return False
    if any(s in t for s in ["table of contents", "contents", "index"]):
        return True

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) >= 8:
        short_lines = sum(1 for ln in lines[:25] if len(ln) <= 60)
        page_like = sum(1 for ln in lines[:25] if any(ch.isdigit() for ch in ln))
        if short_lines >= 6 and page_like >= 3:
            return True
    return False


def _simple_tokens(q: str) -> List[str]:
    q = (q or "").lower()
    q = re.sub(r"[^a-z0-9\s\-]", " ", q)
    toks = [t for t in q.split() if len(t) >= 3]
    # remove noisy instruction words
    bad = {"give", "me", "please", "recipe", "recipes", "for", "the", "a", "an", "of", "to"}
    return [t for t in toks if t not in bad]


def _soft_best_chunk(query: str, chunks: List[RetrievedChunk]) -> Optional[RetrievedChunk]:
    """
    Soft fallback:
    إذا الفلتر رفض الكل، بس في chunk واضح انه قريب من السؤال،
    نختار أفضل واحد بناءً على token hits + score.
    """
    if not chunks:
        return None
    toks = _simple_tokens(query)
    if not toks:
        return chunks[0]

    best = None
    best_score = -1.0
    for ch in chunks:
        text = (ch.content or "").lower()
        hits = sum(1 for t in toks if t in text)
        # tiny bias for vector relevance if available
        rel = 0.0
        if ch.score is not None:
            rel = 1.0 / (1.0 + float(ch.score))
        score = hits + (0.25 * rel)
        if score > best_score:
            best_score = score
            best = ch

    # require at least 1 hit for safety
    if best_score >= 1.0:
        return best
    return None


def is_retrieval_relevant(query: str, chunks: List[RetrievedChunk]) -> bool:
    if not chunks:
        return False

    q = (query or "").lower().strip()

    if _is_catalog_intent(q):
        return any(_looks_like_toc_or_index(c.content) for c in chunks)

    toks = _simple_tokens(q)
    if not toks:
        return True

    joined = "\n".join((c.content or "").lower() for c in chunks)
    hits = sum(1 for t in toks if t in joined)
    return hits >= 1


def retrieve_with_retry(query: str, k: int = 4) -> Tuple[List[RetrievedChunk], str, List[dict]]:
    ql = (query or "").lower().strip()
    is_catalog = _is_catalog_intent(ql)
    pool_k = max(k * (8 if is_catalog else 3), k)

    # ===== 1) Catalog route =====
    if is_catalog:
        toc_queries = [
            "table of contents",
            "contents",
            "index",
            "recipe index",
            "recipes contents",
            query,
        ]

        all_chunks: List[RetrievedChunk] = []
        for tq in toc_queries:
            all_chunks.extend(retrieve_cookbook(tq, k=pool_k))

        toc_like = [c for c in all_chunks if _looks_like_toc_or_index(c.content)]
        if not toc_like:
            return [], "no_toc_found", []

        kept, filtered_out = filter_and_rank_chunks(query, toc_like, max_sources=max(k, 6))
        return (kept or toc_like[: max(k, 6)]), "toc", filtered_out

    # ===== 2) Normal route =====
    chunks = retrieve_cookbook(query, k=pool_k)
    if is_retrieval_relevant(query, chunks):
        kept, filtered_out = filter_and_rank_chunks(query, chunks, max_sources=k)
        if kept:
            return kept, "direct", filtered_out

        # ✅ SOFT FALLBACK: use best chunk instead of weak
        soft = _soft_best_chunk(query, chunks)
        if soft:
            return [soft], "soft", filtered_out

        return chunks[:k], "weak", filtered_out

    refined = f"{query} recipe ingredients"
    chunks2 = retrieve_cookbook(refined, k=pool_k)
    if is_retrieval_relevant(query, chunks2):
        kept, filtered_out = filter_and_rank_chunks(query, chunks2, max_sources=k)
        if kept:
            return kept, "refined", filtered_out

        soft = _soft_best_chunk(query, chunks2)
        if soft:
            return [soft], "soft", filtered_out

        return chunks2[:k], "weak", filtered_out

    if "temperature" in ql or "temp" in ql or "degrees" in ql:
        refined_temp = f"{query} oven temperature degrees set the oven"
        chunks3 = retrieve_cookbook(refined_temp, k=pool_k)
        kept, filtered_out = filter_and_rank_chunks(query, chunks3, max_sources=k)
        if kept:
            return kept, "refined_temp", filtered_out

        soft = _soft_best_chunk(query, chunks3)
        if soft:
            return [soft], "soft", filtered_out

        return chunks3[:k], "weak", filtered_out

    kept, filtered_out = filter_and_rank_chunks(query, chunks2, max_sources=k)
    if kept:
        return kept, "weak", filtered_out

    soft = _soft_best_chunk(query, chunks2)
    if soft:
        return [soft], "soft", filtered_out

    return chunks2[:k], "weak", filtered_out


class AgentAskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
