import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

MEMORY_FILE = Path(__file__).resolve().parent / "memory.json"

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def load_memory() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        return {"facts": [], "turns": []}
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

def save_memory(mem: Dict[str, Any]) -> None:
    MEMORY_FILE.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")

def add_fact(text: str, tag: str = "general") -> None:
    mem = load_memory()
    mem["facts"].append({"text": text.strip(), "tag": tag, "ts": _now()})
    mem["facts"] = mem["facts"][-100:]
    save_memory(mem)

def add_turn(user: str, assistant: str) -> None:
    mem = load_memory()
    mem["turns"].append({"user": user, "assistant": assistant, "ts": _now()})
    mem["turns"] = mem["turns"][-50:]
    save_memory(mem)

def get_recent_facts(limit: int = 8) -> List[str]:
    mem = load_memory()
    return [f["text"] for f in mem.get("facts", [])[-limit:]]
