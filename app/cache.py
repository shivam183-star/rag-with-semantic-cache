import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)


@dataclass
class LookupResult:
    hit: bool
    score: float | None = None            # only set on a hit
    matched_question: str | None = None   # only set on a hit
    answer: str | None = None             # only set on a hit
    sources: list = field(default_factory=list)


class SemanticCache:
    def __init__(
        self,
        client: QdrantClient,
        collection: str,
        embed_fn: Callable[[str], list[float]],
        dim: int,
        threshold: float = 0.90,
        ttl_seconds: int = 7 * 24 * 3600,
    ):
        self.client = client
        self.collection = collection
        self.embed_fn = embed_fn
        self.dim = dim
        self.threshold = threshold
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def normalize(text: str) -> str:
        return " ".join(text.lower().split())

    def ensure(self, recreate: bool = False) -> None:
        if recreate and self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )
        try:  # index speeds up the TTL filter on Qdrant Cloud
            self.client.create_payload_index(
                self.collection, "expires_at", PayloadSchemaType.FLOAT
            )
        except Exception:
            pass  # index might already exist or not supported in local in-memory mode

    def lookup(self, question: str, threshold: float | None = None) -> LookupResult:
        if not self.client.collection_exists(self.collection):
            return LookupResult(hit=False)
        thr = self.threshold if (threshold is None or threshold <= 0) else threshold
        vec = self.embed_fn(self.normalize(question))
        not_expired = Filter(
            must=[FieldCondition(key="expires_at", range=Range(gt=time.time()))]
        )
        res = self.client.query_points(
            collection_name=self.collection,
            query=vec,
            query_filter=not_expired,
            limit=1,
            with_payload=True,
        )
        if not res.points:
            return LookupResult(hit=False)
        point = res.points[0]
        payload = point.payload or {}
        hit = point.score >= thr
        return LookupResult(
            hit=hit,
            score=float(point.score) if hit else None,
            matched_question=payload.get("question") if hit else None,
            answer=payload.get("answer") if hit else None,
            sources=(payload.get("sources") or []) if hit else [],
        )

    def store(self, question: str, answer: str, sources: list) -> None:
        self.ensure()
        now = time.time()
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=self.embed_fn(self.normalize(question)),
                    payload={
                        "question": question,
                        "answer": answer,
                        "sources": sources,
                        "created_at": now,
                        "expires_at": now + self.ttl_seconds,
                    },
                )
            ],
        )

    def count(self) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        return self.client.count(collection_name=self.collection, exact=True).count

    def prune_expired(self) -> int:
        """Delete points whose expires_at <= current time."""
        if not self.client.collection_exists(self.collection):
            return 0
        before = self.count()
        self.client.delete(
            collection_name=self.collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="expires_at", range=Range(lte=time.time()))]
                )
            ),
        )
        return max(0, before - self.count())

    def clear(self) -> None:
        self.ensure(recreate=True)
