from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import get_settings


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
