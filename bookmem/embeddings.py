from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import get_settings

EMBEDDING_PROVIDER = "sentence_transformers"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    if isinstance(embeddings, np.ndarray):
        return embeddings.astype("float32").tolist()

    return embeddings



def embedding_model_name() -> str:
    return str(get_settings().embedding_model)


def embedding_dimension() -> int | None:
    """Return embedding dimension without forcing callers to know model internals."""
    try:
        model = get_model()
        # `get_sentence_embedding_dimension` was renamed to
        # `get_embedding_dimension`; prefer the current name and fall back to
        # the old one for older sentence-transformers releases.
        for method_name in ("get_embedding_dimension", "get_sentence_embedding_dimension"):
            method = getattr(model, method_name, None)
            if callable(method):
                return int(method())
    except Exception:
        return None
    return None
