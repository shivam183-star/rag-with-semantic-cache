"""Usage: python -m scripts.check_retrieval "What is Article 21?" """
import sys

from app.vectorstore import get_docs_store

query = " ".join(sys.argv[1:]) or "What is Article 21?"
for doc, score in get_docs_store().similarity_search_with_score(query, k=4):
    print(f"score={score:.3f}  page={doc.metadata.get('page')}")
    print(doc.page_content[:300].replace("\n", " "), "\n")