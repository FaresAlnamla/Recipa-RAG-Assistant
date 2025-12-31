from pathlib import Path
from pydantic import BaseModel
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCE_DIR = DATA_DIR / "source"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma"

COOKBOOK_PDF = SOURCE_DIR / "COOKBOOK.pdf"


class Settings(BaseModel):
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chroma_collection: str = "cookbook-recipes"
    vectorstore_dir: str | Path = VECTORSTORE_DIR


@lru_cache
def get_settings() -> Settings:
    from dotenv import load_dotenv
    import os

    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
