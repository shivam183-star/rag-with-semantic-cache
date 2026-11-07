import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_logs, get_stats, init_db, log_request
from app.deps import get_cache, get_rag
from app.embeddings import embed_query
from app.rag import NOT_FOUND_TEXT
from app.schemas import AskRequest, AskResponse

log = logging.getLogger("rag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        get_cache().ensure()
    except Exception as exc:
        log.warning("Could not initialize Qdrant cache collection on startup: %s", exc)
    try:
        embed_query("warmup")  # load the embedding model before the first real request
    except Exception as exc:
        log.warning("Embedding warmup failed: %s", exc)
    yield


app = FastAPI(title="RAG Semantic Cache API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "RAG Semantic Cache API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health(cache=Depends(get_cache), rag=Depends(get_rag)):
    return {"status": "ok", "docs_chunks": rag.doc_count(), "cache_entries": cache.count()}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, cache=Depends(get_cache), rag=Depends(get_rag)):
    start = time.perf_counter()

    # 1. Reformulate question using conversation history if present
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
    if history_dicts:
        standalone_q = rag.condense_question(req.question, history_dicts)
    else:
        standalone_q = req.question

    # 2. Check semantic cache using the standalone question
    lookup = cache.lookup(standalone_q, threshold=req.threshold)
    in_tok = out_tok = 0

    if lookup.hit:
        answer, sources = lookup.answer or "", lookup.sources
    elif req.dry_run:
        answer, sources = "", []
    else:
        try:
            result = rag.generate(standalone_q, history=history_dicts)
        except Exception as exc:
            log.exception("LLM pipeline failed")
            raise HTTPException(status_code=502, detail=f"LLM backend error: {exc}")
        answer, sources = result["answer"], result["sources"]
        in_tok, out_tok = result["input_tokens"], result["output_tokens"]
        # Never cache "not found" answers: they may just reflect a retrieval miss.
        if NOT_FOUND_TEXT.lower() not in answer.lower():
            cache.store(standalone_q, answer, sources)

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    log_request(
        question=req.question,
        cache_hit=lookup.hit,
        similarity=lookup.score,
        matched_question=lookup.matched_question,
        latency_ms=latency_ms,
        input_tokens=in_tok,
        output_tokens=out_tok,
        run_tag=req.run_tag,
        dry_run=req.dry_run,
    )
    return AskResponse(
        answer=answer,
        standalone_question=standalone_q if standalone_q != req.question else None,
        cache_hit=lookup.hit,
        similarity=lookup.score,
        matched_question=lookup.matched_question,
        sources=sources,
        latency_ms=latency_ms,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )


@app.get("/stats")
def stats(run_tag: str | None = None):
    return get_stats(run_tag)


@app.get("/logs")
def logs(run_tag: str | None = None, limit: int = 100):
    return get_logs(run_tag, limit)


@app.post("/cache/clear")
def clear_cache(cache=Depends(get_cache)):
    cache.clear()
    return {"cleared": True}


@app.post("/cache/prune")
def prune_cache(cache=Depends(get_cache)):
    pruned = cache.prune_expired()
    return {"pruned_entries": pruned}
