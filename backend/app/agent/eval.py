from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.agent.tools.retrieval_tool import RetrievedChunk


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "were", "can", "could", "should", "would", "what", "when",
    "how", "long", "time", "make", "made", "does", "do", "it", "in", "on", "at",
    "to", "of", "a", "an", "is", "be", "as", "by",

    # ✅ new: common instruction noise
    "give", "me", "please", "kindly", "show", "tell", "provide", "need", "want",
    "recipe", "recipes", "book", "cookbook", "context",
}

UNITS = {
    "°f", "°c", "f", "c", "degrees", "degree",
    "minute", "minutes", "min", "mins",
    "hour", "hours", "hr", "hrs",
    "second", "seconds", "sec", "secs",
}

CATALOG_HINTS = {
    "list", "all", "index", "contents", "table of contents", "toc",
    "what recipes", "which recipes", "recipes are in this book", "recipe list",
    "chapters",
}


def _is_catalog_query(query: str) -> bool:
    q = (query or "").lower().strip()
    if not q:
        return False
    if any(h in q for h in CATALOG_HINTS):
        return True
    if "list of recipes" in q or ("recipes" in q and ("list" in q or "all" in q or "index" in q or "contents" in q)):
        return True
    return False


# ===== Tokenize / overlap =====

def _tokenize(text: str) -> List[str]:
    """
    Tokenize keeping:
    - words
    - numbers
    - patterns like 350°F, 350f, 8-10, 8–10
    """
    text = (text or "").lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9\s\-°]", " ", text)

    toks: List[str] = []
    for t in text.split():
        if t in STOPWORDS:
            continue
        if len(t) < 2:
            continue
        toks.append(t)
    return toks


def _overlap_score(query: str, chunk_text: str) -> float:
    q = set(_tokenize(query))
    if not q:
        return 0.0
    c = set(_tokenize(chunk_text))
    if not c:
        return 0.0
    return len(q & c) / max(1, len(q))


def _relevance_from_score(score: float | None) -> float:
    """
    If Chroma score is distance (lower=better):
    distance -> relevance in [0..1]
    """
    if score is None:
        return 0.0
    return 1.0 / (1.0 + float(score))


def _query_focus_terms(query: str) -> List[str]:
    """
    Extract meaningful focus words from the query (subject).
    ✅ Remove instruction words + generic nouns.
    """
    toks = _tokenize(query)
    out = []
    for t in toks:
        if t in UNITS:
            continue
        if t.isdigit():
            continue
        # ignore too generic words even if not in STOPWORDS
        if t in {"recipe", "recipes", "cookbook", "book", "context"}:
            continue
        if len(t) >= 4:
            out.append(t)

    # dedupe while preserving order
    seen = set()
    final = []
    for t in out:
        if t in seen:
            continue
        seen.add(t)
        final.append(t)
    return final[:5]


def filter_and_rank_chunks(
    query: str,
    chunks: List[RetrievedChunk],
    *,
    max_sources: int = 3,
    min_overlap: float = 0.08,   # ✅ was 0.12
    min_combined: float = 0.38,  # ✅ was 0.45 (too strict)
) -> Tuple[List[RetrievedChunk], List[Dict[str, Any]]]:
    """
    Filtering:
    - overlap + combined score
    - require focus term mention (disabled for catalog queries)
    """
    filtered_out: List[Dict[str, Any]] = []

    is_catalog = _is_catalog_query(query)

    if is_catalog:
        # relax more for TOC/Index queries
        min_overlap = min(min_overlap, 0.03)
        min_combined = min(min_combined, 0.15)
        focus_terms: List[str] = []
    else:
        focus_terms = _query_focus_terms(query)

    scored: List[Tuple[RetrievedChunk, float, float, float]] = []
    for ch in chunks:
        rel = _relevance_from_score(ch.score)
        ov = _overlap_score(query, ch.content)

        content_l = (ch.content or "").lower()
        has_focus = True
        if focus_terms:
            has_focus = any(t in content_l for t in focus_terms)

        combined = (0.30 * rel) + (0.70 * ov)

        if has_focus and (ov >= min_overlap) and (combined >= min_combined):
            scored.append((ch, combined, rel, ov))
        else:
            md = ch.metadata or {}
            filtered_out.append({
                "page_label": md.get("page_label"),
                "page": md.get("page"),
                "score": ch.score,
                "relevance": round(rel, 4),
                "overlap": round(ov, 4),
                "combined": round(combined, 4),
                "focus_terms": focus_terms,
                "reason": "filtered(has_focus/overlap/combined)",
                "catalog_mode": is_catalog,
            })

    scored.sort(key=lambda x: x[1], reverse=True)

    # dedupe by (source, page/page_label)
    seen = set()
    kept: List[RetrievedChunk] = []
    for ch, _, _, _ in scored:
        md = ch.metadata or {}
        key = (md.get("source"), md.get("page_label") or md.get("page"))
        if key in seen:
            continue
        seen.add(key)
        kept.append(ch)
        if len(kept) >= max_sources:
            break

    return kept, filtered_out


# ===== Support evaluation =====

def _extract_key_facts(text: str) -> List[str]:
    t = (text or "").lower().replace("–", "-")

    facts: List[str] = []

    for m in re.finditer(r"\b(\d{1,4})\s*-\s*(\d{1,4})\b", t):
        facts.append(m.group(0).replace(" ", ""))

    for m in re.finditer(r"\b(\d{2,3})\s*(°\s*[fc]|[fc])\b", t):
        facts.append(m.group(1) + m.group(2).replace(" ", ""))

    for m in re.finditer(r"\b(\d{2,3})\s*degrees?\s*([fc])\b", t):
        facts.append(f"{m.group(1)} degrees {m.group(2)}")

    for m in re.finditer(r"\b(\d+\s*(?:-\s*\d+)?)\s*(minutes?|mins?|hours?|hrs?)\b", t):
        val = m.group(1).replace(" ", "")
        unit = m.group(2).lower().replace("mins", "minutes").replace("hrs", "hours")
        facts.append(f"{val} {unit}")

    seen = set()
    out = []
    for f in facts:
        ff = f.strip()
        if not ff or ff in seen:
            continue
        seen.add(ff)
        out.append(ff)
    return out


def evaluate_support(answer: str, context: str) -> Dict[str, Any]:
    ans = (answer or "").strip()
    ctx = (context or "").lower().replace("–", "-")

    if not ans:
        return {"supported": False, "confidence": 0.0, "reasons": ["empty_answer"], "facts_checked": []}

    facts = _extract_key_facts(ans)

    missing: List[str] = []
    for f in facts:
        f_norm = f.lower().replace(" ", "")
        ctx_norm = ctx.replace(" ", "")
        if f_norm and f_norm not in ctx_norm:
            missing.append(f)

    a_tokens = set(_tokenize(ans))
    c_tokens = set(_tokenize(ctx))
    overlap = len(a_tokens & c_tokens) / max(1, len(a_tokens))

    reasons: List[str] = []
    supported = True

    if missing:
        supported = False
        reasons.append(f"missing_facts_in_context: {missing[:6]}")

    confidence = min(1.0, 0.30 + overlap)
    if overlap < 0.08:
        reasons.append("very_low_overlap_with_context")
        confidence = min(confidence, 0.35)

    return {
        "supported": supported,
        "confidence": round(confidence, 3),
        "reasons": reasons or ["ok"],
        "facts_checked": facts[:10],
    }
