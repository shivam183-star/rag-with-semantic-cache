"""Usage: python -m scripts.ingest --pdf data/constitution_of_india.pdf --recreate"""
import argparse
import re
from collections import Counter
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.deps import get_cache
from app.vectorstore import ensure_collection, get_docs_store


def strip_repeated_lines(pages, min_ratio: float = 0.3) -> None:
    """Remove running headers/footers (lines repeated on many pages) and bare page numbers."""
    counts: Counter = Counter()
    for p in pages:
        for line in {l.strip() for l in p.page_content.splitlines() if l.strip()}:
            counts[line] += 1
    cutoff = max(3, int(len(pages) * min_ratio))
    noisy = {line for line, c in counts.items() if c >= cutoff}
    for p in pages:
        kept = [
            l
            for l in p.page_content.splitlines()
            if l.strip() not in noisy and not re.fullmatch(r"\d{1,4}", l.strip())
        ]
        p.page_content = "\n".join(kept)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--chunk-size", type=int, default=1200)
    ap.add_argument("--chunk-overlap", type=int, default=150)
    ap.add_argument("--recreate", action="store_true", help="wipe docs + cache collections first")
    args = ap.parse_args()
    s = get_settings()

    print(f"Loading {args.pdf} ...")
    pages = PyMuPDFLoader(args.pdf).load()
    for p in pages:
        p.metadata = {"source": Path(args.pdf).name, "page": int(p.metadata.get("page", 0)) + 1}
    strip_repeated_lines(pages)
    pages = [p for p in pages if len(p.page_content.strip()) > 50]
    print(f"Usable pages: {len(pages)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = [c for c in splitter.split_documents(pages) if len(c.page_content.strip()) > 50]

    article_pattern = re.compile(r"\b(?:Article\s+)?(\d+[A-Z]?)\.\s+([A-Z][^\n\.]*)")
    for c in chunks:
        m = article_pattern.search(c.page_content)
        if m:
            c.metadata["article"] = f"Article {m.group(1)}"

    print(f"Chunks: {len(chunks)}")

    ensure_collection(s.docs_collection, recreate=args.recreate)
    # The document changed, so old cached answers are invalid: reset the cache too.
    get_cache().ensure(recreate=args.recreate)

    store = get_docs_store()
    batch = 64
    for i in range(0, len(chunks), batch):
        store.add_documents(chunks[i : i + batch])
        print(f"Upserted {min(i + batch, len(chunks))}/{len(chunks)}")
    print("Done.")


if __name__ == "__main__":
    main()
