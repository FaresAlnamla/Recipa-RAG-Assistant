from pydantic import BaseModel
from typing import List, Optional

class SourceItem(BaseModel):
    page: Optional[int] = None          # 0-index from loader
    page_label: Optional[str] = None    # human page label
    source: Optional[str] = None        # full file path
    book_name: Optional[str] = None     # ✅ NEW: Friendly book name for display
    answer: str
    sources: List[SourceItem]
