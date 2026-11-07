from functools import lru_cache

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings
from app.embeddings import get_embeddings


@lru_cache
def get_client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key, timeout=30)


def ensure_collection(name: str, recreate: bool = False) -> None:
    client = get_client()
    if recreate and client.collection_exists(name):
        client.delete_collection(name)
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=get_settings().embedding_dim, distance=Distance.COSINE
            ),
        )


def get_docs_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_client(),
        collection_name=get_settings().docs_collection,
        embedding=get_embeddings(),
    )