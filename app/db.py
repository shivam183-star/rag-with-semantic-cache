from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

_url = get_settings().database_url
engine = create_engine(
    _url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    question = Column(Text, nullable=False)
    cache_hit = Column(Boolean, nullable=False)
    similarity = Column(Float, nullable=True)
    matched_question = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    run_tag = Column(String(64), nullable=True)
    dry_run = Column(Boolean, default=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def reset_db() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def log_request(**fields) -> None:
    with SessionLocal() as s:
        s.add(RequestLog(**fields))
        s.commit()


def get_logs(run_tag: str | None = None, limit: int = 100) -> list[dict]:
    with SessionLocal() as s:
        q = s.query(RequestLog)
        if run_tag:
            q = q.filter(RequestLog.run_tag == run_tag)
        rows = q.order_by(RequestLog.id.desc()).limit(limit).all()
    return [{c.name: getattr(r, c.name) for c in RequestLog.__table__.columns} for r in rows]


def get_stats(run_tag: str | None = None) -> dict:
    with SessionLocal() as s:
        q = s.query(RequestLog).filter(
            (RequestLog.dry_run == False) | (RequestLog.dry_run.is_(None))  # noqa: E712
        )
        if run_tag:
            q = q.filter(RequestLog.run_tag == run_tag)
        rows = q.all()

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    def p95(xs):
        if not xs:
            return None
        sorted_xs = sorted(xs)
        idx = int(0.95 * len(sorted_xs))
        return round(sorted_xs[min(idx, len(sorted_xs) - 1)], 2)

    hits = [r for r in rows if r.cache_hit]
    misses = [r for r in rows if not r.cache_hit]
    total = len(rows)
    miss_tokens = [(r.input_tokens or 0) + (r.output_tokens or 0) for r in misses]
    avg_miss_tokens = avg([t for t in miss_tokens if t > 0])

    avg_hit_lat = avg([r.latency_ms for r in hits])
    avg_miss_lat = avg([r.latency_ms for r in misses])
    latency_red_pct = None
    if avg_hit_lat is not None and avg_miss_lat is not None and avg_miss_lat > 0:
        latency_red_pct = round(((avg_miss_lat - avg_hit_lat) / avg_miss_lat) * 100, 2)

    return {
        "total_requests": total,
        "hits": len(hits),
        "misses": len(misses),
        "hit_rate": round(len(hits) / total, 4) if total else 0.0,
        "miss_rate": round(len(misses) / total, 4) if total else 0.0,
        "avg_latency_ms_hit": avg_hit_lat,
        "avg_latency_ms_miss": avg_miss_lat,
        "p95_latency_ms_hit": p95([r.latency_ms for r in hits]),
        "p95_latency_ms_miss": p95([r.latency_ms for r in misses]),
        "latency_reduction_pct": latency_red_pct,
        "avg_tokens_per_miss": avg_miss_tokens,
        "estimated_tokens_saved": round(len(hits) * avg_miss_tokens) if avg_miss_tokens else 0,
    }
