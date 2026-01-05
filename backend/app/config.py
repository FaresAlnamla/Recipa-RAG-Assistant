from pathlib import Path
from pydantic import BaseModel
from functools import lru_cache
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCE_DIR = DATA_DIR / "source"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = Path(os.getenv("VECTORSTORE_DIR", str(BASE_DIR / "vectorstore" / "chroma")))

COOKBOOK_PDF = SOURCE_DIR / "COOKBOOK.pdf"


class Settings(BaseModel):
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chroma_collection: str = "cookbook-recipes"
    vectorstore_dir: str | Path = VECTORSTORE_DIR
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    from dotenv import load_dotenv

    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        chat_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "cookbook-recipes"),
        vectorstore_dir=Path(os.getenv("VECTORSTORE_DIR", str(VECTORSTORE_DIR))),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000"),
        environment=os.getenv("ENVIRONMENT", "development"),
    )
