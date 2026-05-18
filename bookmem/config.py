from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    books_dir: Path = Path("./data/books")
    db_dir: Path = Path("./data/lancedb")
    table_name: str = "book_chunks"
    taxonomy_path: Path = Path("./config/bmdc.yaml")
    manifest_path: Path | None = None
    summaries_dir: Path | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_target_chars: int = 3500
    chunk_overlap_chars: int = 500


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        books_dir=Path(os.getenv("BOOKMEM_BOOKS_DIR", "./data/books")),
        db_dir=Path(os.getenv("BOOKMEM_DB_DIR", "./data/lancedb")),
        table_name=os.getenv("BOOKMEM_TABLE", "book_chunks"),
        taxonomy_path=Path(os.getenv("BOOKMEM_TAXONOMY_PATH", "./config/bmdc.yaml")),
        manifest_path=Path(os.getenv("BOOKMEM_MANIFEST_PATH")) if os.getenv("BOOKMEM_MANIFEST_PATH") else None,
        summaries_dir=Path(os.getenv("BOOKMEM_SUMMARIES_DIR")) if os.getenv("BOOKMEM_SUMMARIES_DIR") else None,
        embedding_model=os.getenv(
            "BOOKMEM_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        chunk_target_chars=int(os.getenv("BOOKMEM_CHUNK_TARGET_CHARS", "3500")),
        chunk_overlap_chars=int(os.getenv("BOOKMEM_CHUNK_OVERLAP_CHARS", "500")),
    )
