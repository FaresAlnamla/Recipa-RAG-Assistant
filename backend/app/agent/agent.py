from __future__ import annotations

import re
from typing import Any, Dict, Generator, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.eval import evaluate_support
from app.agent.memory import add_message, get_history, get_last_user_question
from app.agent.router import decide_route, retrieve_with_retry
from app.agent.tools.retrieval_tool import RetrievedChunk
from app.config import get_settings


SYSTEM_PROMPT = """You are RecipaAI, an autonomous cooking assistant for the book 'The Low-Cost Cookbook'.

Rules:
- Your ONLY source of factual information is the provided cookbook context.
- If the cookbook context does NOT contain the answer, say you cannot find it in the cookbook.
- Do NOT guess or use external knowledge.
- Be clear and concise.
- If helpful, include cooking times/temps exactly as written.
- Answer ONLY what the user asked for.
  - If the user asks only for temperature, output temperature only.
  - If the user asks only for time, output time only.
- Respond in the same language as the user's question.
- When copying cookbook text, keep it exactly as written.
- You can answer questions about:
  * Recipe instructions and cooking methods
  * Ingredients and ingredient substitutions
  * Cooking times, temperatures, and preparation times
  * Serving sizes and yields
  * Cheap/budget-friendly meal ideas
  * The cookbook itself (author, publication info, etc.)
  * Lists of recipes available in the book
  * Any other information that appears in the cookbook
"""


FOLLOWUP_STARTERS = (
    "and ",
    "also ",
    "what about ",
    "how about ",
    "then ",
    "so ",
)

# ✅ expanded followup keywords to catch: prep time / servings / cook time
FOLLOWUP_KEYWORDS = {
    "temperature", "temp", "degrees", "°f", "°c",
    "how long", "time", "minutes", "mins", "hours", "hrs",
    "serves", "servings", "yield",
    "prep", "prep time", "cook time",
    "can i", "could i", "should i", "what if",
    "instead", "substitute", "replace", "change",
    "add", "remove", "skip", "omit",
    "put", "topping", "toppings", "serve", "serving", "suggest",
    "what about", "how about", "instructions", "steps",
}

CATALOG_HINTS = {
    "list", "all", "index", "contents", "table of contents", "toc",
    "what recipes", "which recipes", "recipes are in this book", "recipe list",
    "chapters",
}

# ===== Recipe State Machine (NEXT STEP) =====
STATE_NONE = "NONE"
STATE_IN_RECIPE = "IN_RECIPE"

SYS_ACTIVE_RECIPE = "[active_recipe]"
SYS_RECIPE_STATE = "[recipe_state]"

# ===== Recipe Cache (NEXT STEP++) =====
# store last good chunks/context for the active recipe, to avoid retrieval drift
SYS_RECIPE_CACHE = "[recipe_cache]"        # stores a short cache key
SYS_RECIPE_CACHE_META = "[recipe_cache_meta]"  # stores page/source labels (optional)


def _is_arabic_text(s: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", s or ""))


def _note_missing_steps(user_query: str) -> str:
    if _is_arabic_text(user_query):
        return "ملاحظة: الكتاب بالكونتكست المقدم ما بذكر خطوات خطوة بخطوة لهاي الوصفة."
    return "Note: The provided cookbook context does not include step-by-step instructions for this recipe."


def _is_catalog_query(q: str) -> bool:
    q = (q or "").strip().lower()
    if not q:
        return False
    if any(h in q for h in CATALOG_HINTS):
        return True
    if "list of recipes" in q or ("recipes" in q and ("list" in q or "all" in q or "index" in q or "contents" in q)):
        return True
    if "are these the only" in q or "only recipes" in q:
        return True
    return False


def _looks_like_followup(q: str) -> bool:
    """
    ✅ improved:
    - old logic: starters, and short queries with followup keywords
    - new logic: also treat medium-length questions that are clearly followup-ish
      like: "What is the prep time and how many servings does it make?"
    - newer logic: treat short questions as followups by default if they have pronouns/refs
    """
    q = (q or "").strip().lower()
    if not q:
        return False

    if q.startswith(FOLLOWUP_STARTERS):
        return True

    # any keyword => likely followup (allow longer than 6 words now)
    if any(k in q for k in FOLLOWUP_KEYWORDS):
        # avoid treating full new recipe requests as followup
        if any(x in q for x in ["recipe for", "give me the recipe", "how to make", "ingredients for"]):
            return False
        # allow up to ~16 words for followups
        if len(q.split()) <= 16:
            return True

    # Treat very short questions with pronouns/references as likely followups
    # e.g., "what did you suggest?", "how long?", "what about it?"
    if len(q.split()) <= 6:
        ref_pronouns = ["what", "how", "did you", "you", "it", "that"]
        if any(ref in q for ref in ref_pronouns):
            return True

    return False


def _extract_recipe_subject(last_q: str) -> Optional[str]:
    if not last_q:
        return None
    s = last_q.lower()
    
    # Try pattern: "bake/cook/make <recipe>"
    m = re.search(r"\b(?:bake|cook|make)\s+(.*?)(?:\?|$)", s)
    if m:
        subj = m.group(1).strip(" .")
        subj = " ".join(subj.split()[:6])
        return subj
    
    # Try pattern: "What is <recipe>" or similar (handles "What is peanut butter cookies?")
    m = re.search(r"\b(?:what is|what are|tell me about|is it a|are these)\s+(.*?)(?:\?|$)", s)
    if m:
        subj = m.group(1).strip(" .")
        subj = " ".join(subj.split()[:6])
        return subj
    
    # Fallback: take all words except common prefixes
    words = s.split()
    if len(words) > 2:
        # skip common question words at start
        start_skip = ["what", "how", "when", "where", "why", "is", "are", "do", "does", "did", "can", "could", "should"]
        idx = 0
        for word in words:
            word_clean = word.strip("?,.!;:")
            if word_clean not in start_skip:
                break
            idx += 1
        
        remaining = " ".join(words[idx:])
        remaining = remaining.strip("?,.!;: ")
        if remaining:
            remaining = " ".join(remaining.split()[:6])
            return remaining
    
    return None


def _rewrite_followup(user_query: str, session_id: str) -> Tuple[str, Optional[str]]:
    q = (user_query or "").strip()
    if not _looks_like_followup(q):
        return q, None

    last_q = get_last_user_question(session_id, offset=1)
    if not last_q:
        return q, None

    # Try to get active recipe from session cache first
    active_recipe = _get_active_recipe(session_id)
    
    # Extract subject from previous question or use active recipe
    subject = None
    if active_recipe:
        subject = active_recipe
    else:
        subject = _extract_recipe_subject(last_q)
    
    if not subject:
        subject = last_q  # Fallback to full previous question

    q_low = q.lower()
    if "temp" in q_low or "temperature" in q_low or "degrees" in q_low:
        expanded = f"What temperature do I bake {subject} at? (oven temperature in degrees F/C)"
        return expanded, last_q

    expanded = f"For '{subject}', {q}"
    return expanded, last_q


def _clean_query_for_retrieval(q: str) -> str:
    """
    ✅ Make retrieval robust:
    remove instruction fluff مثل:
    "give me", "please", "recipe for", punctuation
    """
    q = (q or "").strip()
    if not q:
        return q
    low = q.lower().strip()

    low = re.sub(r"^\s*(please|kindly)\s+", "", low)
    low = re.sub(r"^\s*(give me|show me|tell me|provide)\s+", "", low)
    low = re.sub(r"\b(recipe for|the recipe for|a recipe for)\b", " ", low)

    low = re.sub(r"\bhow\s+to\s+(make|cook|prepare)\b", " ", low)
    low = re.sub(r"\bhow\s+do\s+i\s+(make|cook|prepare)\b", " ", low)

    low = re.sub(r"[^a-z0-9\s\-]", " ", low)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def _format_context(chunks: List[RetrievedChunk]) -> str:
    lines: List[str] = []
    for i, ch in enumerate(chunks, 1):
        meta = ch.metadata or {}
        page = meta.get("page_label") or meta.get("page")
        src = meta.get("source")
        header = f"[Chunk {i} | page={page} | source={src}]"
        lines.append(header)
        lines.append((ch.content or "").strip())
        lines.append("")
    return "\n".join(lines).strip()


def _extract_book_name_from_path(path: Optional[str]) -> Optional[str]:
    """
    Extract friendly book name from file path.
    E.g., "C:\\path\\to\\cookbook.pdf" -> "cookbook"
    Handles multiple books by extracting filename without extension.
    """
    if not path:
        return None
    try:
        import os
        filename = os.path.basename(path)
        book_name = os.path.splitext(filename)[0]
        # Special-case mapping for known cookbook filename patterns to exact display
        key = (book_name or "").lower()
        if "low" in key and "cost" in key:
            # User requested full title for The Low-Cost Cookbook
            return "THE LOW-COST COOKBOOK"

        # Default: replace underscores/dashes with spaces and title-case
        return book_name.replace("_", " ").replace("-", " ").strip().title() if book_name else None
    except Exception:
        return None


def _build_sources(chunks: List[RetrievedChunk], limit: int = 2) -> List[Dict[str, Any]]:
    seen = set()
    sources: List[Dict[str, Any]] = []
    for ch in chunks:
        md = ch.metadata or {}
        key = (md.get("source"), md.get("page_label") or md.get("page"))
        if key in seen:
            continue
        seen.add(key)

        # ✅ Extract book name from source path for display
        book_name = _extract_book_name_from_path(md.get("source"))

        sources.append(
            {
                "page_label": md.get("page_label"),
                "page": md.get("page"),
                "source": md.get("source"),
                "book_name": book_name,  # ✅ NEW: Friendly book name
                "snippet": ((ch.content or "")[:180]).replace("\n", " ").strip(),
            }
        )
    return sources[:limit]


def _history_to_messages(history: List[Dict[str, str]]):
    msgs = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
        elif role == "system":
            msgs.append(SystemMessage(content=content))
    return msgs


# ==========================
# ✅ NEW: multi-field extractors
# ==========================

def _extract_serves(text: str) -> Optional[str]:
    m = re.search(r"\bserves\b\s*[:\-]?\s*(\d+)", text or "", re.IGNORECASE)
    if m:
        return m.group(1)

    m2 = re.search(r"(?is)\bserves\b\s*\n\s*(\d+)", text or "")
    if m2:
        return m2.group(1)

    return None


def _extract_prep_time(text: str) -> Optional[str]:
    t = text or ""
    m = re.search(r"(?is)\bprep\s*time\b\s*[:\-]?\s*(\d+\s*(?:-\s*\d+)?)\s*(minutes?|mins?|hours?|hrs?)", t)
    if m:
        val = m.group(1).replace(" ", "")
        unit = m.group(2).lower().replace("mins", "minutes").replace("hrs", "hours")
        return f"{val} {unit}"

    m2 = re.search(r"(?is)\bprep\s*time\b\s*\n\s*(\d+\s*(?:-\s*\d+)?)\s*(minutes?|mins?|hours?|hrs?)", t)
    if m2:
        val = m2.group(1).replace(" ", "")
        unit = m2.group(2).lower().replace("mins", "minutes").replace("hrs", "hours")
        return f"{val} {unit}"

    return None


def _ask_kind(q: str) -> str:
    ql = (q or "").lower()

    wants_prep = ("prep time" in ql) or ("prep" in ql and "time" in ql)
    wants_serves = ("serves" in ql) or ("servings" in ql) or ("how many" in ql and ("servings" in ql or "serves" in ql))

    if wants_prep and wants_serves:
        return "prep_and_serves"
    if wants_prep:
        return "prep"
    if wants_serves:
        return "serves"

    if any(x in ql for x in ["temperature", "temp", "degrees", "°f", "°c"]):
        return "temperature"
    if any(x in ql for x in ["how long", "time", "minutes", "mins", "hours", "hrs", "seconds", "secs"]):
        return "time"

    return "general"


def _extract_temperature(text: str) -> Optional[str]:
    m = re.search(r"(\d{2,3})\s*(?:degrees?\s*)?(°?\s*[fc])\b", text or "", re.IGNORECASE)
    if m:
        num = m.group(1)
        unit = m.group(2).replace(" ", "").upper().replace("°", "")
        return f"{num}°{unit}"
    m2 = re.search(r"(\d{2,3})\s*degrees", text or "", re.IGNORECASE)
    if m2:
        return f"{m2.group(1)} degrees"
    return None


def _extract_time(text: str) -> Optional[str]:
    m = re.search(
        r"(\d+\s*(?:-\s*\d+)?)\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)\b",
        text or "",
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).replace(" ", "")
        unit = m.group(2).lower()
        unit = unit.replace("mins", "minutes").replace("hrs", "hours").replace("secs", "seconds")
        return f"{val} {unit}"
    return None


def _short_answer_postprocess(kind: str, answer: str, context: str) -> str:
    if kind == "temperature":
        t = _extract_temperature(answer) or _extract_temperature(context)
        return t or answer

    if kind == "time":
        t = _extract_time(answer) or _extract_time(context)
        return t or answer

    if kind == "prep":
        p = _extract_prep_time(answer) or _extract_prep_time(context)
        return p or answer

    if kind == "serves":
        s = _extract_serves(answer) or _extract_serves(context)
        return s or answer

    if kind == "prep_and_serves":
        p = _extract_prep_time(context) or _extract_prep_time(answer)
        s = _extract_serves(context) or _extract_serves(answer)

        if p and s:
            return f"Prep Time: {p}\nServes: {s}"
        if p:
            return f"Prep Time: {p}"
        if s:
            return f"Serves: {s}"
        return answer

    return answer


def _toc_not_found_response() -> str:
    return (
        "فتّشت بالكونتكست اللي عندي، بس ما لقيت صفحة فهرس/Contents أو قائمة وصفات واضحة. "
        "عشان هيك ما بقدر أحكيلك كل الوصفات الموجودة بالكتاب بشكل مؤكد. "
        "إذا بتضيف صفحات الـ Contents/Index للكونتكست، بطلعلك القائمة كاملة."
    )


def _context_has_steps(context: str) -> bool:
    t = (context or "").lower()
    if not t:
        return False

    if any(k in t for k in ["directions", "method", "instructions", "steps", "procedure"]):
        return True

    if re.search(r"(?m)^\s*\d+\s*[\.\)]\s+\w+", t):
        return True

    verbs = ["mix", "stir", "add", "combine", "cook", "heat", "bake", "serve", "spread", "drain", "chop"]
    verb_hits = sum(1 for v in verbs if re.search(rf"\b{v}\b", t))
    if verb_hits >= 4:
        return True

    return False


def _user_wants_steps(q: str) -> bool:
    q = (q or "").lower()
    return any(p in q for p in ["how to make", "how do i make", "how to cook", "how to prepare", "method", "instructions", "steps"])


# ============================
# ✅ Recipe Context Lock helpers
# ============================

def _normalize_title(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _extract_recipe_title_from_context(context: str) -> Optional[str]:
    if not context:
        return None

    lines = []
    for raw in context.splitlines():
        t = raw.strip()
        if not t:
            continue
        if t.startswith("[Chunk "):
            continue
        lines.append(t)
        if len(lines) >= 10:
            break

    if not lines:
        return None

    joined = " ".join(lines[:2]).strip()
    joined = re.split(r"\bingredients\b", joined, flags=re.IGNORECASE)[0].strip()

    if len(joined) < 4:
        return None

    joined = re.sub(r"[^\w\s\-]", "", joined).strip()
    joined = _normalize_title(joined)
    return joined or None


def _get_system_value(history: List[Dict[str, str]], prefix: str) -> Optional[str]:
    for h in reversed(history or []):
        if h.get("role") == "system":
            c = (h.get("content") or "").strip()
            if c.startswith(prefix):
                return c.replace(prefix, "", 1).strip()
    return None


def _get_active_recipe(session_id: str) -> Optional[str]:
    history = get_history(session_id, limit=60)
    return _get_system_value(history, SYS_ACTIVE_RECIPE)


def _get_recipe_state(session_id: str) -> str:
    history = get_history(session_id, limit=60)
    st = _get_system_value(history, SYS_RECIPE_STATE)
    return st or STATE_NONE


def _set_recipe_state(session_id: str, state: str) -> None:
    add_message(session_id, "system", f"{SYS_RECIPE_STATE} {state}")


def _set_active_recipe(session_id: str, title: str) -> None:
    title = _normalize_title(title)
    if not title:
        return
    add_message(session_id, "system", f"{SYS_ACTIVE_RECIPE} {title}")
    _set_recipe_state(session_id, STATE_IN_RECIPE)


def _clear_active_recipe(session_id: str) -> None:
    add_message(session_id, "system", f"{SYS_ACTIVE_RECIPE} ")
    _set_recipe_state(session_id, STATE_NONE)
    _clear_recipe_cache(session_id)


def _is_new_recipe_request(q: str) -> bool:
    ql = (q or "").lower()
    return any(p in ql for p in [
        "give me the recipe", "recipe for", "ingredients for",
        "how to make", "how do i make", "how to prepare",
    ])


def _apply_recipe_lock_if_followup(session_id: str, user_query: str, retrieval_query: str) -> str:
    if not _looks_like_followup(user_query):
        return retrieval_query

    active = _get_active_recipe(session_id)
    if not active:
        return retrieval_query

    return _clean_query_for_retrieval(f"{active} {retrieval_query}")


# ============================
# ✅ Recipe Cache helpers (NEXT STEP++)
# ============================

def _serialize_cached_chunks(chunks: List[RetrievedChunk], max_chars: int = 12000) -> str:
    """
    Store only minimal info to rebuild context later.
    Format per chunk:
    ---CHUNK---
    page_label=..|page=..|source=..
    <content>
    """
    out: List[str] = []
    used = 0
    for ch in chunks or []:
        md = ch.metadata or {}
        header = f"page_label={md.get('page_label')}|page={md.get('page')}|source={md.get('source')}"
        body = (ch.content or "").strip()
        block = f"---CHUNK---\n{header}\n{body}\n"
        if used + len(block) > max_chars:
            break
        out.append(block)
        used += len(block)
    return "".join(out).strip()


def _deserialize_cached_chunks(payload: str) -> List[RetrievedChunk]:
    if not payload:
        return []
    chunks: List[RetrievedChunk] = []
    parts = payload.split("---CHUNK---")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = p.splitlines()
        if not lines:
            continue
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        md: Dict[str, Any] = {}
        for seg in header.split("|"):
            if "=" in seg:
                k, v = seg.split("=", 1)
                md[k.strip()] = None if v.strip() in ("None", "") else v.strip()

        # normalize page fields
        if "page" in md and isinstance(md["page"], str) and md["page"].isdigit():
            md["page"] = int(md["page"])

        chunks.append(RetrievedChunk(content=body, metadata=md))
    return chunks


def _set_recipe_cache(session_id: str, title: str, chunks: List[RetrievedChunk]) -> None:
    title = _normalize_title(title)
    if not title or not chunks:
        return
    payload = _serialize_cached_chunks(chunks)
    if not payload:
        return
    add_message(session_id, "system", f"{SYS_RECIPE_CACHE} {title}")
    add_message(session_id, "system", f"{SYS_RECIPE_CACHE_META}\n{payload}")


def _get_recipe_cache(session_id: str) -> Tuple[Optional[str], List[RetrievedChunk]]:
    history = get_history(session_id, limit=80)
    title = _get_system_value(history, SYS_RECIPE_CACHE)
    payload = None
    for h in reversed(history or []):
        if h.get("role") == "system":
            c = (h.get("content") or "").strip()
            if c.startswith(SYS_RECIPE_CACHE_META):
                payload = c.replace(SYS_RECIPE_CACHE_META, "", 1).strip()
                break
    return (title or None), _deserialize_cached_chunks(payload or "")


def _clear_recipe_cache(session_id: str) -> None:
    add_message(session_id, "system", f"{SYS_RECIPE_CACHE} ")
    add_message(session_id, "system", f"{SYS_RECIPE_CACHE_META} ")


def _should_use_cache(user_query: str, final_query: str, session_id: str) -> bool:
    """
    Use cache ONLY for followups when we have active recipe and cached chunks.
    Avoid cache for new recipe requests or catalog.
    """
    if _is_catalog_query(user_query) or _is_catalog_query(final_query):
        return False
    if _is_new_recipe_request(final_query):
        return False
    if not _looks_like_followup(user_query):
        return False

    active = _get_active_recipe(session_id)
    if not active:
        return False

    cached_title, cached_chunks = _get_recipe_cache(session_id)
    if not cached_title or not cached_chunks:
        return False

    # ensure cache belongs to same active recipe (best-effort)
    return _normalize_title(cached_title) == _normalize_title(active)


def answer_with_agent(user_query: str, session_id: Optional[str] = "default") -> dict:
    user_query = (user_query or "").strip()
    session_id = (session_id or "default").strip()

    if not user_query:
        return {
            "answer": "Please type your question.",
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["empty_query"], "facts_checked": []},
            "filtered_out": [],
        }

    add_message(session_id, "user", user_query)

    kind = _ask_kind(user_query)

    final_query, rewritten_from = _rewrite_followup(user_query, session_id)
    if rewritten_from and final_query != user_query:
        add_message(session_id, "system", f"[followup_rewrite] {user_query} -> {final_query}")

    is_catalog = _is_catalog_query(user_query) or _is_catalog_query(final_query)

    if is_catalog:
        _clear_active_recipe(session_id)

    retrieval_query = _clean_query_for_retrieval(final_query)

    # ✅ Apply recipe lock for follow-ups (prevents drifting to other recipes)
    retrieval_query = _apply_recipe_lock_if_followup(session_id, user_query, retrieval_query)

    decision = decide_route(final_query)
    if not decision.use_cookbook:
        _clear_active_recipe(session_id)
        return {
            "answer": "I can only answer questions that can be answered from the cookbook.",
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["out_of_scope"], "facts_checked": []},
            "filtered_out": [],
        }

    # ✅ Recipe Cache: use cached chunks for followups (skip retrieval entirely)
    used_cache = False
    cached_chunks: List[RetrievedChunk] = []
    cached_title: Optional[str] = None
    if _should_use_cache(user_query, final_query, session_id):
        cached_title, cached_chunks = _get_recipe_cache(session_id)
        if cached_chunks:
            chunks = cached_chunks
            mode = "cache"
            filtered_out = []
            used_cache = True
        else:
            chunks, mode, filtered_out = retrieve_with_retry(retrieval_query, k=4)
    else:
        chunks, mode, filtered_out = retrieve_with_retry(retrieval_query, k=4)

    if mode == "no_toc_found" or (is_catalog and not chunks):
        return {
            "answer": _toc_not_found_response(),
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["toc_not_found"], "facts_checked": []},
            "filtered_out": filtered_out,
        }

    if mode == "weak":
        if is_catalog:
            return {
                "answer": _toc_not_found_response(),
                "sources": [],
                "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["weak_retrieval_catalog"], "facts_checked": []},
                "filtered_out": filtered_out,
            }
        return {
            "answer": (
                "I searched the cookbook but I couldn’t find a clear answer for that. "
                "Try rephrasing your question or mention the exact recipe name if it exists in the book."
            ),
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["weak_retrieval"], "facts_checked": []},
            "filtered_out": filtered_out,
        }

    context = _format_context(chunks)

    # ✅ sources: from chunks whether cached or retrieved
    sources = _build_sources(chunks, limit=4 if is_catalog else 2)

    settings = get_settings()
    llm = ChatOpenAI(model=settings.chat_model, api_key=settings.openai_api_key)

    history = get_history(session_id, limit=10)
    history_msgs = _history_to_messages(history)

    extra = ""
    if kind == "temperature":
        extra = "\nReturn ONLY the temperature (e.g., 350°F). No extra words."
    elif kind == "time":
        extra = "\nReturn ONLY the baking/cooking time (e.g., 8-10 minutes). No extra words."

    toc_extra = ""
    if is_catalog:
        toc_extra = """
You are answering a "list of recipes in the book" question.
- ONLY list recipe titles that are explicitly present in the provided cookbook context.
- Do NOT claim this is the complete list unless the context clearly shows a full Table of Contents / Index.
- If the context looks partial, say: "This appears to be a partial list from the available context."
- Output as a bullet list only (one recipe title per bullet).
"""

    soft_extra = ""
    if mode == "soft":
        soft_extra = """
Note: Retrieval returned a best-matching chunk (soft match).
Answer ONLY using the chunk text. If key details are missing, say you cannot find them in the cookbook.
"""

    missing_steps_rule = ""
    wants_steps = _user_wants_steps(final_query)
    has_steps = _context_has_steps(context)

    if wants_steps and not has_steps:
        note = _note_missing_steps(user_query)
        missing_steps_rule = f"""
If the user asks "how to make / steps / instructions" but the cookbook context provides only ingredients/time (no clear steps),
then:
- Return the ingredients + any times/servings exactly as written from the context.
- Add this note exactly at the end: "{note}"
- Do NOT invent any steps.
"""

    user_prompt = f"""Question:
{final_query}

Cookbook context:
{context}

Answer using ONLY the cookbook context above.
If the answer is not present, say you cannot find it in the cookbook.
{missing_steps_rule}
{extra}
{toc_extra}
{soft_extra}
"""

    resp = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), *history_msgs, HumanMessage(content=user_prompt)])
    answer = (resp.content or "").strip()

    # ✅ ensures temp/time/prep/serves/prep+serves are extracted deterministically
    answer = _short_answer_postprocess(kind, answer, context)

    add_message(session_id, "assistant", answer)

    # ✅ Recipe state machine:
    # If this looks like a recipe request OR we’re already in recipe mode -> set/refresh active recipe from context
    if not is_catalog:
        state = _get_recipe_state(session_id)
        is_follow = _looks_like_followup(user_query)
        is_new_recipe = _is_new_recipe_request(final_query)

        if is_new_recipe or (state == STATE_IN_RECIPE) or is_follow:
            title = _extract_recipe_title_from_context(context)
            # Fallback: try to extract a title from the first retrieved chunk if context parsing failed
            if not title and chunks:
                try:
                    first = chunks[0]
                    first_line = (first.content or "").splitlines()[0]
                    cand = re.split(r"\bingredients\b", first_line, flags=re.IGNORECASE)[0].strip()
                    if cand and len(cand) >= 3:
                        title = _normalize_title(cand)
                except Exception:
                    title = None

            if title:
                _set_active_recipe(session_id, title)

            # ✅ cache: only set cache when we are in/entering recipe mode AND retrieval produced good chunks (not cache itself)
            # If already using cache, keep it.
            active = _get_active_recipe(session_id)
            if active and (not used_cache) and chunks:
                _set_recipe_cache(session_id, active, chunks)

    evaluation = evaluate_support(answer, context)

    # ✅ Don't show sources if answer indicates "cannot find" or answer is very short/negative
    sources_to_show = sources
    if any(phrase in answer.lower() for phrase in [
        "cannot find",
        "i cannot find",
        "couldn't find",
        "i couldn't find",
        "not in the cookbook",
        "not present in",
        "not available",
        "not clear",
    ]):
        sources_to_show = []

    return {
        "answer": answer,
        "sources": sources_to_show,
        "evaluation": evaluation,
        "filtered_out": filtered_out,
    }


def answer_with_agent_stream(
    user_query: str,
    session_id: Optional[str] = "default",
) -> Generator[Dict[str, Any], None, None]:
    user_query = (user_query or "").strip()
    session_id = (session_id or "default").strip()

    if not user_query:
        yield {
            "type": "done",
            "answer": "",
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["empty_query"], "facts_checked": []},
            "filtered_out": [],
        }
        return

    add_message(session_id, "user", user_query)

    kind = _ask_kind(user_query)

    final_query, rewritten_from = _rewrite_followup(user_query, session_id)
    if rewritten_from and final_query != user_query:
        add_message(session_id, "system", f"[followup_rewrite] {user_query} -> {final_query}")

    is_catalog = _is_catalog_query(user_query) or _is_catalog_query(final_query)
    if is_catalog:
        _clear_active_recipe(session_id)

    retrieval_query = _clean_query_for_retrieval(final_query)
    retrieval_query = _apply_recipe_lock_if_followup(session_id, user_query, retrieval_query)

    decision = decide_route(final_query)
    if not decision.use_cookbook:
        _clear_active_recipe(session_id)
        yield {
            "type": "done",
            "answer": "I can only answer questions that can be answered from the cookbook.",
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["out_of_scope"], "facts_checked": []},
            "filtered_out": [],
        }
        return

    # ✅ Recipe Cache in streaming too
    used_cache = False
    if _should_use_cache(user_query, final_query, session_id):
        _, cached_chunks = _get_recipe_cache(session_id)
        if cached_chunks:
            chunks = cached_chunks
            mode = "cache"
            filtered_out = []
            used_cache = True
        else:
            chunks, mode, filtered_out = retrieve_with_retry(retrieval_query, k=4)
    else:
        chunks, mode, filtered_out = retrieve_with_retry(retrieval_query, k=4)

    if mode == "no_toc_found" or (is_catalog and not chunks):
        yield {
            "type": "done",
            "answer": _toc_not_found_response(),
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["toc_not_found"], "facts_checked": []},
            "filtered_out": filtered_out,
        }
        return

    if mode == "weak":
        if is_catalog:
            yield {
                "type": "done",
                "answer": _toc_not_found_response(),
                "sources": [],
                "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["weak_retrieval_catalog"], "facts_checked": []},
                "filtered_out": filtered_out,
            }
            return

        yield {
            "type": "done",
            "answer": (
                "I searched the cookbook but I couldn’t find a clear answer for that. "
                "Try rephrasing your question or mention the exact recipe name if it exists in the book."
            ),
            "sources": [],
            "evaluation": {"supported": False, "confidence": 0.0, "reasons": ["weak_retrieval"], "facts_checked": []},
            "filtered_out": filtered_out,
        }
        return

    context = _format_context(chunks)
    sources = _build_sources(chunks, limit=4 if is_catalog else 2)

    # ✅ deterministic answers for structured fields (skip streaming mismatch)
    if kind in ("temperature", "time", "prep", "serves", "prep_and_serves"):
        result = answer_with_agent(user_query, session_id=session_id)
        yield {
            "type": "done",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "evaluation": result.get("evaluation", None),
            "filtered_out": result.get("filtered_out", []),
        }
        return

    settings = get_settings()
    llm = ChatOpenAI(model=settings.chat_model, api_key=settings.openai_api_key, streaming=True)

    history = get_history(session_id, limit=10)
    history_msgs = _history_to_messages(history)

    toc_extra = ""
    if is_catalog:
        toc_extra = """
You are answering a "list of recipes in the book" question.
- ONLY list recipe titles that are explicitly present in the provided cookbook context.
- Do NOT claim this is the complete list unless the context clearly shows a full Table of Contents / Index.
- If the context looks partial, say: "This appears to be a partial list from the available context."
- Output as a bullet list only (one recipe title per bullet).
"""

    soft_extra = ""
    if mode == "soft":
        soft_extra = """
Note: Retrieval returned a best-matching chunk (soft match).
Answer ONLY using the chunk text. If key details are missing, say you cannot find them in the cookbook.
"""

    missing_steps_rule = ""
    wants_steps = _user_wants_steps(final_query)
    has_steps = _context_has_steps(context)
    if wants_steps and not has_steps:
        note = _note_missing_steps(user_query)
        missing_steps_rule = f"""
If the user asks "how to make / steps / instructions" but the cookbook context provides only ingredients/time (no clear steps),
then:
- Return the ingredients + any times/servings exactly as written from the context.
- Add this note exactly at the end: "{note}"
- Do NOT invent any steps.
"""

    user_prompt = f"""Question:
{final_query}

Cookbook context:
{context}

Answer using ONLY the cookbook context above.
If the answer is not present, say you cannot find it in the cookbook.
{missing_steps_rule}
{toc_extra}
{soft_extra}
"""

    answer_accum: List[str] = []
    for chunk in llm.stream([SystemMessage(content=SYSTEM_PROMPT), *history_msgs, HumanMessage(content=user_prompt)]):
        token = getattr(chunk, "content", "") or ""
        if token:
            answer_accum.append(token)
            yield {"type": "token", "token": token}

    final_answer = "".join(answer_accum).strip()
    add_message(session_id, "assistant", final_answer)

    # ✅ Recipe state machine update after streamed answer
    if not is_catalog:
        state = _get_recipe_state(session_id)
        is_follow = _looks_like_followup(user_query)
        is_new_recipe = _is_new_recipe_request(final_query)

        if is_new_recipe or (state == STATE_IN_RECIPE) or is_follow:
            title = _extract_recipe_title_from_context(context)
            # Fallback: try to extract a title from the first retrieved chunk if context parsing failed
            if not title and chunks:
                try:
                    first = chunks[0]
                    first_line = (first.content or "").splitlines()[0]
                    cand = re.split(r"\bingredients\b", first_line, flags=re.IGNORECASE)[0].strip()
                    if cand and len(cand) >= 3:
                        title = _normalize_title(cand)
                except Exception:
                    title = None

            if title:
                _set_active_recipe(session_id, title)

            # ✅ set cache if we retrieved chunks (not using cache)
            active = _get_active_recipe(session_id)
            if active and (not used_cache) and chunks:
                _set_recipe_cache(session_id, active, chunks)

    evaluation = evaluate_support(final_answer, context)

    # ✅ Don't show sources if answer indicates "cannot find" or answer is very short/negative
    sources_to_show = sources
    if any(phrase in final_answer.lower() for phrase in [
        "cannot find",
        "i cannot find",
        "couldn't find",
        "i couldn't find",
        "not in the cookbook",
        "not present in",
        "not available",
        "not clear",
    ]):
        sources_to_show = []

    yield {
        "type": "done",
        "answer": final_answer,
        "sources": sources_to_show,
        "evaluation": evaluation,
        "filtered_out": filtered_out,
    }

