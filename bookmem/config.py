from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic import BaseModel

from . import paths


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


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None


def get_settings() -> Settings:
    """Resolve settings.

    Directory defaults come from the central path resolver (:mod:`bookmem.paths`),
    so they honour ``--home``, ``BOOKMEM_HOME``, the active profile and Hermes
    auto-detection. Individual ``BOOKMEM_*`` environment variables still override
    specific paths for power users and container deployments.
    """
    load_dotenv()
    return Settings(
        books_dir=_env_path("BOOKMEM_BOOKS_DIR") or paths.books_dir(),
        db_dir=_env_path("BOOKMEM_DB_DIR") or paths.lancedb_dir(),
        table_name=os.getenv("BOOKMEM_TABLE", "book_chunks"),
        taxonomy_path=_env_path("BOOKMEM_TAXONOMY_PATH") or (paths.config_dir() / "bmdc.yaml"),
        manifest_path=_env_path("BOOKMEM_MANIFEST_PATH"),
        summaries_dir=_env_path("BOOKMEM_SUMMARIES_DIR") or paths.summaries_dir(),
        embedding_model=os.getenv(
            "BOOKMEM_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        chunk_target_chars=int(os.getenv("BOOKMEM_CHUNK_TARGET_CHARS", "3500")),
        chunk_overlap_chars=int(os.getenv("BOOKMEM_CHUNK_OVERLAP_CHARS", "500")),
    )
