from functools import lru_cache

from langchain_community.embeddings import FastEmbedEmbeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> FastEmbedEmbeddings:
    # The model (~130 MB) downloads on first use, then is cached on disk.
    return FastEmbedEmbeddings(model_name=get_settings().embedding_model)


def embed_query(text: str) -> list[float]:
    return get_embeddings().embed_query(text)