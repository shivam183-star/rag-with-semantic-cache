rag-semantic-cache/
├── app/
│   ├── __init__.py
│   ├── config.py          # settings from .env
│   ├── embeddings.py      # FastEmbed wrapper
│   ├── vectorstore.py     # Qdrant client + collections
│   ├── cache.py           # semantic cache
│   ├── rag.py             # retrieval + Groq generation
│   ├── db.py              # request logging + stats
│   ├── schemas.py         # API models
│   ├── deps.py            # singletons for FastAPI
│   └── main.py            # FastAPI app
├── scripts/
│   ├── __init__.py
│   ├── ingest.py          # PDF -> Qdrant
│   ├── check_retrieval.py # sanity check for ingestion
│   ├── generate_questions.py
│   └── run_eval.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cache.py
│   └── test_api.py
├── data/                  # put the PDF here
├── eval/                  # questions.json and results
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pytest.ini
└── requirements.txt