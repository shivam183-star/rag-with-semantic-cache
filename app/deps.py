from functools import lru_cache

from langchain_groq import ChatGroq

from app.cache import SemanticCache
from app.config import get_settings
from app.embeddings import embed_query
from app.rag import RAGPipeline
from app.vectorstore import get_client, get_docs_store


@lru_cache
def get_cache() -> SemanticCache:
    s = get_settings()
    return SemanticCache(
        client=get_client(),
        collection=s.cache_collection,
        embed_fn=embed_query,
        dim=s.embedding_dim,
        threshold=s.cache_threshold,
        ttl_seconds=s.cache_ttl_seconds,
    )


@lru_cache
def get_rag() -> RAGPipeline:
    s = get_settings()
    llm = ChatGroq(model=s.llm_model, temperature=0, max_tokens=600, api_key=s.groq_api_key)
    condense_llm = ChatGroq(model=s.small_llm_model, temperature=0, max_tokens=150, api_key=s.groq_api_key)

    def count_docs() -> int:
        client = get_client()
        if not client.collection_exists(s.docs_collection):
            return 0
        return client.count(collection_name=s.docs_collection, exact=True).count

    return RAGPipeline(
        store=get_docs_store(),
        llm=llm,
        condense_llm=condense_llm,
        count_fn=count_docs,
        top_k=s.top_k,
    )
