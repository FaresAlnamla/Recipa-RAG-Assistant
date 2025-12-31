from pydantic import BaseModel
from typing import List, Optional

class SourceItem(BaseModel):
    page: Optional[int] = None          # 0-index from loader
    page_label: Optional[str] = None    # human page label
    source: Optional[str] = None
    snippet: str

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
