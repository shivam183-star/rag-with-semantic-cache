# RAG Chatbot with Semantic Caching

**Project Overview and Tech Stack Requirements**

Prepared by: Shivam Singh (Roll No. BTECH/15112/24) | November 2026

## 1. Project Summary

This project builds a Retrieval-Augmented Generation (RAG) chatbot that answers questions from a large PDF document, with a **semantic cache** placed in front of the language model. When a new question is semantically similar to one answered before, the system returns the stored answer instead of calling the LLM again. Every request is logged as a cache **hit** or **miss**, and the system is evaluated on a set of 100 common questions drawn from the document.

The project has two goals:

1. Build a working, deployed RAG system using industry-standard frameworks and only free tools.
2. Measure, with real data, how much a semantic cache reduces latency and LLM usage, and how threshold choice affects the trade-off between hit rate and incorrect (false) hits.

## 2. Problem Statement

RAG systems call an LLM for every question, even when users keep asking the same things in different words. This wastes time and tokens, and it runs into free-tier rate limits quickly. An exact-match cache does not help, because "What is Article 21?" and "Explain the right to life under Article 21" are different strings. A semantic cache compares meaning instead of text, so paraphrased questions can reuse earlier answers.

## 3. Objectives

- Ingest a large PDF and make it searchable through a vector database.
- Answer questions using only retrieved document context, with page or article citations.
- Implement a semantic cache with a configurable similarity threshold and time-to-live (TTL).
- Log every request with hit/miss status, similarity score, latency, and token usage.
- Evaluate the system on 100 common questions plus their paraphrases and out-of-scope questions.
- Analyse the effect of different similarity thresholds on hit rate and false-hit rate.
- Deploy the system on free-tier cloud services and run the final evaluation against the deployed URL.

## 4. Scope

**In scope**

- Single-document question answering over one large PDF.
- Semantic caching of question-to-answer pairs.
- Hit/miss tracking, metrics storage, and a dashboard.
- Cloud deployment on free tiers.

**Out of scope**

- Multi-document or multi-tenant support.
- User authentication and per-user personalisation.
- Fine-tuning any model.
- Multi-turn conversational memory (each question is treated independently, which keeps cache behaviour clean to analyse).

## 5. Source Document

The recommended document is the **Constitution of India (English edition)**, published by the Legislative Department, Ministry of Law and Justice. Reasons:

- Hundreds of pages, with articles, parts, and schedules, which gives a large and well-structured corpus.
- Official government publication, free to use.
- Naturally produces common questions that people phrase in many ways.
- Answers map to specific articles, so correctness of cache hits can be checked.

The pipeline is document-agnostic, so any other large PDF can be substituted. The edition date on the preface page should be recorded in the final report.

## 6. System Architecture

```
User -> Streamlit UI / Dashboard
          |
          v
     FastAPI backend (Cloud Run)
          |
          |-- 1. Embed question (FastEmbed, bge-small-en-v1.5)
          |-- 2. Search semantic_cache collection (Qdrant Cloud)
          |        |-- score >= threshold -> HIT: return cached answer
          |        |-- otherwise          -> MISS: continue
          |-- 3. Retrieve top-k chunks from docs collection (Qdrant Cloud)
          |-- 4. Generate answer with Groq LLM
          |-- 5. Store question embedding + answer in semantic_cache
          |-- 6. Log request to Postgres (Neon/Supabase)
          v
     Answer + cache status + latency
```

### Request flow in detail

1. The question is embedded into a vector.
2. The cache collection is searched for the nearest previously answered question, using cosine similarity.
3. If the best score meets the threshold and the entry has not expired, the cached answer is returned and no LLM call is made.
4. On a miss, the system retrieves the top-k document chunks, builds a prompt restricted to that context, and calls Groq.
5. The new question embedding and answer are written to the cache with a timestamp.
6. The request is logged with its outcome and timings.

### Offline ingestion flow

PDF -> parse (PyMuPDF) -> clean headers and footers -> chunk by article or recursive splitting -> embed -> upsert into the `docs` collection with page and article metadata. Ingestion runs once on a local machine or in CI, not inside the serving container.

## 7. Technology Stack

| Layer | Tool | Purpose |
| --- | --- | --- |
| LLM | Groq API: `llama-3.3-70b-versatile` (answers), `llama-3.1-8b-instant` (paraphrase generation, bulk tasks) | Fast free-tier inference |
| Embeddings | `BAAI/bge-small-en-v1.5` via FastEmbed (ONNX, CPU) | Local, free, small footprint, no PyTorch needed |
| RAG framework | LangChain (`langchain`, `langchain-community`, `langchain-groq`, `langchain-qdrant`) | Loaders, splitters, retriever, prompt and chain composition |
| PDF parsing | PyMuPDF (`PyMuPDFLoader`) | Fast, reliable text extraction |
| Chunking | `RecursiveCharacterTextSplitter`, 500 to 800 tokens, 10 to 15 percent overlap | Balanced retrieval granularity |
| Document vector store | Qdrant Cloud (free tier) | Managed, persistent vector search |
| Semantic cache | Second Qdrant collection (`semantic_cache`) with custom logic | Threshold, TTL, and logging fully controlled in code |
| Metrics database | Neon or Supabase Postgres (free tier) | Persistent request logs that survive restarts |
| Backend API | FastAPI + Uvicorn | REST endpoints |
| Frontend | Streamlit | Chat UI and live metrics dashboard |
| Hosting (API) | Google Cloud Run (free tier, scale to zero) | Containerised deployment |
| Hosting (UI) | Streamlit Community Cloud or a second Cloud Run service | Free UI hosting |
| Secrets | Google Secret Manager | API keys and connection strings |
| CI/CD | GitHub Actions | Auto-deploy on push to `main` |
| Observability | Langfuse Cloud (free tier) | Traces, latency, token usage |
| Evaluation | RAGAS (Groq as judge) plus custom hit/miss scripts | Answer quality and cache metrics |
| Data analysis | pandas, matplotlib or plotly | Result tables and charts |
| Containerisation | Docker | Reproducible builds |

All components have a free tier or are open source. Cloud Run requires a billing account to be enabled, but light usage stays within the free allowance.

## 8. Semantic Cache Design

| Parameter | Design choice |
| --- | --- |
| Key | Embedding of the user question |
| Value | Final answer text, source citations, creation time |
| Similarity metric | Cosine similarity (the same metric as the document collection) |
| Default threshold | 0.90, tuned experimentally between 0.80 and 0.95 |
| TTL | Configurable, for example 7 days, so stale answers expire if the document changes |
| Storage | Qdrant collection `semantic_cache`, with the answer and timestamp in the payload |
| Eviction | TTL-based expiry; optional size cap |
| Normalisation | Lower-case and whitespace-trim before embedding |

The cache logic is written directly against the Qdrant client (roughly 40 lines) rather than through a framework wrapper. This makes the threshold, scores, and hit/miss events explicit, which is what the analysis requires.

## 9. Functional Requirements

| ID | Requirement |
| --- | --- |
| FR1 | The system ingests a PDF and stores chunk embeddings with page and article metadata. |
| FR2 | The API accepts a question and returns an answer, a cache status (hit or miss), a similarity score, and source citations. |
| FR3 | On a hit, the system returns the cached answer without calling the LLM. |
| FR4 | On a miss, the system retrieves top-k chunks, calls the LLM, and stores the result in the cache. |
| FR5 | The cache threshold and TTL are configurable through environment variables. |
| FR6 | Every request is logged with timestamp, question, hit/miss, score, matched cached question, latency, and tokens used. |
| FR7 | The UI shows a chat interface and displays cache status for each answer. |
| FR8 | The dashboard shows hit rate, miss rate, latency comparison, and hit rate over time. |
| FR9 | A batch evaluation script runs the 100-question set and exports results to CSV. |
| FR10 | The system answers "not found in the document" when retrieved context does not support an answer. |

## 10. Non-Functional Requirements

| Category | Requirement |
| --- | --- |
| Performance | Cache hit responses in under 200 ms server-side; miss responses typically 1 to 4 seconds. |
| Cost | Entire system runs on free tiers. |
| Reliability | Retry with exponential backoff on Groq rate-limit errors; request timeouts on all external calls. |
| Security | No secrets in code or images; keys held in Secret Manager or environment variables. |
| Reproducibility | Pinned dependency versions; Dockerfile and one-command local setup. |
| Maintainability | Modular files for ingestion, pipeline, cache, API, and UI. |
| Observability | Every request traceable through logs and Langfuse. |

## 11. Evaluation Plan

### 11.1 Question set

- **100 base questions** covering the main topics in the document, with a reference answer or article number for each.
- **2 to 3 paraphrases per question**, generated with the Groq 8B model and manually spot-checked.
- **15 to 20 near-miss questions** that look similar to base questions but ask something different (for example, a different article number), to test false hits.
- **15 to 20 out-of-scope questions** unrelated to the document, to test refusal and cache isolation.

### 11.2 Test phases

1. **Cold run:** send the 100 base questions with an empty cache. Expect almost all misses.
2. **Warm run:** send the paraphrases. A good cache should produce mostly hits.
3. **Adversarial run:** send near-miss and out-of-scope questions. These should mostly miss.
4. **Threshold sweep:** repeat phases 2 and 3 at thresholds 0.80, 0.85, 0.90, and 0.95.

### 11.3 Metrics

| Metric | Definition |
| --- | --- |
| Hit rate | Hits divided by total requests |
| Miss rate | Misses divided by total requests |
| False-hit rate | Hits where the cached answer belonged to a different question, divided by total hits |
| Latency (hit vs miss) | Mean and p95 response time for each group |
| LLM calls saved | Number of requests answered without calling Groq |
| Tokens saved | Estimated tokens avoided on hits |
| Answer quality | RAGAS faithfulness and answer relevance on a sample of answers |

### 11.4 Expected outputs

- A results table for each threshold.
- A chart of hit rate against false-hit rate across thresholds, used to justify the chosen default.
- A latency comparison chart for hits and misses.
- A CSV of all requests from the evaluation run.

## 12. Deployment Plan

- **Ingestion:** run locally once to populate Qdrant Cloud.
- **API:** FastAPI packaged in a Docker image, with the embedding model downloaded at build time to avoid slow cold starts. Deployed to Cloud Run with 1 vCPU and 1 GiB memory.
- **Instances:** minimum instances set to 0 normally, and to 1 during evaluation runs and demos.
- **UI:** Streamlit app calling the deployed API, hosted on Streamlit Community Cloud.
- **Secrets:** `GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and `DATABASE_URL` stored in Secret Manager.
- **CI/CD:** a GitHub Actions workflow builds and deploys on every push to `main`.
- **Final evaluation:** executed against the deployed URL so reported results reflect the real deployment.

## 13. Repository Structure

```
rag-semantic-cache/
|-- ingest.py            # PDF -> chunks -> Qdrant docs collection
|-- rag_pipeline.py      # retrieval + Groq generation (LangChain)
|-- semantic_cache.py    # cache lookup/store + hit/miss logging
|-- api.py               # FastAPI endpoints
|-- app.py               # Streamlit UI + dashboard
|-- eval/
|   |-- questions.json   # base questions, paraphrases, near-miss, out-of-scope
|   |-- run_eval.py      # batch run, outputs CSV
|   `-- analyse.py       # threshold sweep and charts
|-- Dockerfile
|-- docker-compose.yml   # local development (Qdrant)
|-- requirements.txt     # pinned versions
|-- .github/workflows/deploy.yml
`-- README.md
```

## 14. Free-Tier Constraints and Risks

| Risk | Mitigation |
| --- | --- |
| Groq rate limits interrupt the 100-question runs | Backoff and retry; use the 8B model for bulk tasks; space runs across sessions |
| Qdrant free cluster suspended after inactivity | Ping before demos; keep a local ingestion script to rebuild quickly |
| Cloud Run cold starts | Bake the model into the image; set min instances to 1 during evaluation |
| False cache hits return wrong answers | Tune threshold; include near-miss tests; report false-hit rate openly |
| PDF parsing noise degrades retrieval | Inspect parsed pages; strip headers and footers; fall back to an alternative edition of the PDF |
| LangChain API changes break code | Pin versions in `requirements.txt` |
| Document updated after caching | TTL on cache entries; clear the cache on re-ingestion |

## 15. Milestones

| Phase | Tasks |
| --- | --- |
| 1. Setup | Create accounts (Groq, Qdrant Cloud, Neon, GCP, Langfuse); set up repository and environment |
| 2. Ingestion | Download PDF, parse, clean, chunk, embed, and load into Qdrant |
| 3. Core RAG | Build retrieval and Groq generation; test answer quality manually |
| 4. Semantic cache | Implement lookup, store, threshold, TTL, and hit/miss logging |
| 5. API and UI | FastAPI endpoints, Streamlit chat, and dashboard |
| 6. Evaluation set | Write 100 questions, generate paraphrases, add near-miss and out-of-scope sets |
| 7. Deployment | Dockerise, deploy to Cloud Run and Streamlit, configure CI/CD |
| 8. Experiments | Run cold, warm, adversarial, and threshold-sweep tests on the deployed system |
| 9. Report | Analyse results, produce charts, write the final report and demo |

## 16. Deliverables

- Source code repository with README and setup instructions.
- Deployed API and UI with public URLs.
- Evaluation dataset (`questions.json`) and raw results CSV.
- Final report with architecture, methodology, results tables, charts, and threshold analysis.
- Short demo showing live hit and miss behaviour.

## 17. Success Criteria

- The system answers document questions with correct citations on a manual sample.
- Paraphrase hit rate is high at the chosen threshold, with a false-hit rate that is low and explicitly reported.
- Cache hits are clearly faster than misses and avoid LLM calls.
- The full system runs on free tiers and is accessible through a public URL.
