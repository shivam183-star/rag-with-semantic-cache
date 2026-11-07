# Enterprise RAG Engine with Semantic Caching

A production-grade Retrieval-Augmented Generation (RAG) system with a high-performance vector semantic cache placed ahead of the Large Language Model inference pipeline. Built over the Constitution of India (400+ pages), the architecture intercepts semantically similar queries to eliminate redundant LLM invocations, drastically reducing response latency and API token expenditures.

---

## Live Deployment

- **Live Demo (Vercel Frontend)**: `https://rag-with-semantic-cache.vercel.app/`
- **API Documentation (Swagger UI)**: `https://rag-with-semantic-cache.onrender.com/docs` 

---

## Quantitative Performance Benchmarks

In conventional RAG implementations, every incoming query triggers embedding generation, vector retrieval, and an expensive LLM generation call, leading to high latency and rapid rate-limit exhaustion. By introducing a similarity-thresholded vector cache layer with TTL eviction, this system achieves the following measured performance gains:

| Metric | Direct LLM (Cache Miss) | Semantic Cache (Cache Hit) | Performance Delta |
| :--- | :--- | :--- | :--- |
| **Average Response Latency** | 2,599.18 ms | 887.73 ms | **65.85% reduction** |
| **95th Percentile (p95) Latency** | 3,425.32 ms | 1,004.05 ms | **70.69% reduction** |
| **Token Consumption** | ~1,408 tokens / query | **0 tokens** | **100.00% token savings** |
| **Paraphrase Cache Hit Rate** | N/A | 86.7% | High semantic reuse |
| **Adversarial False-Hit Rate** | N/A | 0.0% (at 0.90 threshold) | Zero false positives |

*Evaluation benchmark conducted across cold baseline runs, semantic paraphrases, and adversarial near-miss test sets.*

---

## Core Architecture and Data Flow

```
                      +-----------------------------+
                      |     React Client (Vercel)   |
                      +-----------------------------+
                                     |
                                     | POST /ask (question, history)
                                     v
                      +-----------------------------+
                      |     FastAPI Backend (Render)|
                      +-----------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Multi-Turn Query Contextualizer       |
                 | (Condenses follow-ups to standalone)  |
                 +---------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | FastEmbed (BAAI/bge-small-en-v1.5)    |
                 +---------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Qdrant Cloud (semantic_cache)         |
                 | Cosine Similarity Check (Thr >= 0.90) |
                 +---------------------------------------+
                       /                          \
             [Hit: Score >= 0.90]         [Miss: Score < 0.90]
                     /                              \
                    v                                v
     +--------------------------+       +--------------------------+
     | Return Cached Answer     |       | Qdrant Cloud (docs)      |
     | (Latency < 900ms, 0 tok) |       | Top-k Passage Retrieval  |
     +--------------------------+       +--------------------------+
                                                     |
                                                     v
                                        +--------------------------+
                                        | Groq API (Inference)     |
                                        | Model: openai/gpt-oss    |
                                        +--------------------------+
                                                     |
                                                     v
                                        +--------------------------+
                                        | Upsert to semantic_cache |
                                        | (with TTL & Citations)   |
                                        +--------------------------+
                                                     |
                                                     v
                                        +--------------------------+
                                        | Log to SQLite / Postgres |
                                        +--------------------------+
```

### Multi-Turn Conversational Caching Strategy

Caching multi-turn conversational interactions introduces the pronoun reference problem:
- Turn 1: *"What is Article 21 of the Indian Constitution?"*
- Turn 2: *"What exceptions does it have?"*

Raw query embedding of *"What exceptions does it have?"* fails because the vector lacks context. Conversely, embedding the entire dialogue history makes every session vector unique, driving the cache hit rate to zero.

This system addresses the challenge through **Context-Aware Query Condensation**:
1. When conversation history is present, a lightweight Groq model (`openai/gpt-oss-20b`) reformulates the follow-up query into a standalone sentence: *"What exceptions does Article 21 of the Indian Constitution have?"*.
2. The standalone query is checked against `semantic_cache`. If another user or session previously asked about Article 21 exceptions, it yields an **immediate cache hit**.
3. On a cache miss, the system retrieves document context and generates a conversational response that respects the dialogue flow.
4. The answer is stored under the standalone query key, preserving high cache reusability across all users.

---

## Technology Stack

### Backend and Inference
- **Framework**: FastAPI, Uvicorn, Pydantic v2
- **LLM Inference**: Groq API (`openai/gpt-oss-120b` for answer generation, `openai/gpt-oss-20b` for query reformulation)
- **Embedding Generation**: FastEmbed (`BAAI/bge-small-en-v1.5`, 384-dimensional dense vectors, ONNX runtime)
- **Vector Database**: Qdrant Cloud (dual collections: `docs` and `semantic_cache` with payload schema indexing)
- **Document Processing**: PyMuPDF (`fitz`), LangChain Text Splitters
- **Metrics Database**: SQLAlchemy with SQLite (local development) / PostgreSQL (production)

### Frontend Client
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS (technical dark-mode interface, non-gradient design system)
- **Icons**: Lucide React
- **HTTP Client**: Native Fetch API with CORS integration

---

## Repository Structure

```
rag-semantic-cache/
|-- app/
|   |-- __init__.py
|   |-- cache.py              # Semantic cache lookup, upsert, TTL pruning
|   |-- config.py             # Pydantic BaseSettings configuration
|   |-- db.py                 # Telemetry logging and aggregate statistics
|   |-- deps.py               # Dependency injection singletons
|   |-- embeddings.py         # FastEmbed dense embedding wrapper
|   |-- main.py               # FastAPI application, routes, and lifespan
|   |-- rag.py                # Multi-turn RAG pipeline, TOC extraction, retrieval
|   |-- schemas.py            # Pydantic request and response models
|   `-- vectorstore.py        # Qdrant client connection and store factory
|-- data/
|   `-- constitution_of_india.pdf   # Source reference corpus (400+ pages)
|-- eval/
|   |-- questions.json        # Curated benchmark dataset (base, paraphrase, near-miss)
|   `-- evaluation_results.csv# Exported evaluation run metrics
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   |-- ChatMessage.jsx     # Message bubble, telemetry chips, sources drawer
|   |   |   |-- Header.jsx          # Connection indicator and quick actions
|   |   |   `-- MetricsDrawer.jsx   # Slide-out dashboard, threshold slider, logs table
|   |   |-- api.js                  # Frontend API client
|   |   |-- App.jsx                 # Application state and chat orchestration
|   |   |-- index.css               # Tailwind directives
|   |   `-- main.jsx                # Application root entry
|   |-- index.html
|   |-- package.json
|   |-- tailwind.config.js
|   |-- vercel.json           # SPA routing rewrite configuration
|   `-- vite.config.js
|-- scripts/
|   |-- __init__.py
|   |-- check_retrieval.py    # CLI sanity check for vector retrieval
|   |-- ingest.py             # PDF text extraction, cleaning, chunking, indexing
|   `-- run_eval.py           # Automated evaluation benchmark runner
|-- .env.example              # Environment variables template
|-- .gitignore
|-- render.yaml               # Infrastructure-as-code for Render deployment
|-- requirements.txt          # Pinned Python package dependencies
`-- README.md
```

---

## Installation and Setup

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- A free [Groq Cloud](https://console.groq.com) API Key
- A free [Qdrant Cloud](https://cloud.qdrant.io) Cluster URL and API Key

### 1. Clone the Repository
```bash
git clone https://github.com/shivam183-star/rag-with-semantic-cache.git
cd rag-with-semantic-cache
```

### 2. Configure Backend Environment
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key
LLM_MODEL=openai/gpt-oss-120b
SMALL_LLM_MODEL=openai/gpt-oss-20b

QDRANT_URL=https://your-cluster-id.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
DOCS_COLLECTION=docs
CACHE_COLLECTION=semantic_cache

CACHE_THRESHOLD=0.90
CACHE_TTL_SECONDS=604800
TOP_K=8

DATABASE_URL=sqlite:///./metrics.db
```

### 3. Ingest the Document
Index the source PDF into Qdrant Cloud:
```bash
python -m scripts.ingest --pdf data/constitution_of_india.pdf --recreate
```

### 4. Run the Backend API Server
```bash
uvicorn app.main:app --reload --port 8000
```
The API documentation will be accessible at `http://127.0.0.1:8000/docs`.

### 5. Setup and Run the React Frontend
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## Evaluation Benchmark

The repository includes an evaluation harness designed to test cache precision, latency reduction, and token avoidance.

To run the automated sweep across all benchmark categories:
```bash
python -m scripts.run_eval --url http://127.0.0.1:8000 --threshold 0.90
```

The script executes three sequential phases:
1. **Cold Phase**: Submits base reference questions to establish baseline latency and token counts.
2. **Warm Phase**: Submits semantic paraphrases to measure hit rate and latency reduction.
3. **Adversarial Phase**: Submits near-miss variants to verify that false cache hits do not occur.

Results are exported to `eval/evaluation_results.csv`.

---

## REST API Specification

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Service status and root health indicator. |
| `/health` | `GET` | Returns chunk count in `docs` and active points in `semantic_cache`. |
| `/ask` | `POST` | Primary conversational interface. Accepts question, history, threshold, and dry_run flag. |
| `/stats` | `GET` | Aggregated telemetry metrics (hit rate, miss rate, average latencies, p95, tokens saved). |
| `/logs` | `GET` | Detailed historical logs of requests, scores, and timings. |
| `/cache/prune` | `POST` | Triggers explicit eviction of entries whose TTL has expired. |
| `/cache/clear` | `POST` | Wipes and resets the semantic cache collection. |

### Sample Request (`POST /ask`)
```json
{
  "question": "What is Article 21 of the Indian Constitution?",
  "history": [],
  "threshold": 0.90,
  "run_tag": "eval_test",
  "dry_run": false
}
```

### Sample Response
```json
{
  "answer": "Article 21 guarantees the protection of life and personal liberty, stating that no person shall be deprived of his life or personal liberty except according to procedure established by law (p. 42).",
  "standalone_question": null,
  "cache_hit": true,
  "similarity": 0.954,
  "matched_question": "What is Article 21?",
  "sources": [
    {
      "page": 42,
      "article": "Article 21",
      "snippet": "21. Protection of life and personal liberty. No person shall be deprived of his life or personal liberty except according to procedure established by law."
    }
  ],
  "latency_ms": 118.42,
  "input_tokens": 0,
  "output_tokens": 0
}
```

---

# 📄 License

This project is licensed under the [MIT License](LICENSE).

---

# Author

## Shivam Singh

### Connect with Me

- [GitHub](https://github.com/shivam183-star)
- [LinkedIn](https://www.linkedin.com/in/shivam-singh-15b79a31a/)
---

# Support

If you found this project useful:

- Give it a ⭐ on GitHub
- Share it with others
- Fork the repository

---

# Note

This project is intended for educational and portfolio purposes.