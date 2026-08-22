# Technical Documentation Assistant

A self-corrective RAG system built with **LangGraph** + **FastAPI**, answering
questions over a small FastAPI-documentation corpus with retrieval, LLM-based
document grading, query rewriting on failure, and cited answers.

## Architecture

```
START
  │
  ▼
analyze_query ──────────────┐   (rewrites the question, classifies query_type)
  │                         │
  ▼                         │  loop back on retry
retrieve                    │   (top-k similarity search, ChromaDB)
  │                         │
  ▼                         │
grade_documents ─────────────┘
  │
  ├── relevant docs found ─────────► generate ──► END
  │                                  (cited answer, grounded in context)
  │
  └── no relevant docs
        ├── retries remaining ──► (back to analyze_query, rewritten query)
        └── retries exhausted ──► fallback ──► END  ("I don't know")
```

`grade_documents` is the self-corrective component: it's the only node that
writes `retry_count`, incrementing it exactly when an attempt finds zero
relevant chunks. The conditional edge (`route_after_grading`) just reads that
counter, so retry bookkeeping lives in one place instead of being split
across nodes.

### State schema (`src/state.py`)

```python
class RAGState(TypedDict, total=False):
    question: str
    rewritten_query: str
    query_type: str
    documents: List[RetrievedDoc]          # raw retrieval results
    graded_documents: List[RetrievedDoc]   # filtered to relevant only
    retry_count: int
    max_retries: int
    answer: str
    sources: List[str]
    gave_up: bool
```

## Corpus

`data/docs/` contains 5 short, self-authored Markdown reference pages on
FastAPI (path parameters, request bodies, dependency injection, background
tasks, testing) — enough to demonstrate retrieval + grading without needing
an external fetch step. Swap in your own `.md`/`.txt` files and re-run
ingestion to use a different corpus.

## Chunking & Embedding Strategy

1. **Markdown-header split first** (`##` boundaries) so a chunk never
   straddles two unrelated subsections.
2. **Recursive character split** within each section, `chunk_size=800`,
   `chunk_overlap=120` — small enough to keep retrieval precise (~1
   concept/chunk), large enough to keep a code snippet and its explanation
   together.
3. **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`, run locally via
   `langchain-huggingface` — free, no API key, 384-dim, fast enough for a
   5-document corpus. Swap to OpenAI/Cohere embeddings in
   `src/vectorstore.py` if you need higher quality on a larger corpus.
4. **Store**: ChromaDB, persisted to `./chroma_db/`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set an LLM API key. Default provider is **Groq** (free tier,
fast) — get a key at https://console.groq.com. To use OpenAI instead, set
`LLM_PROVIDER=openai` and `OPENAI_API_KEY`.

Ingest the sample corpus:

```bash
python scripts/ingest_corpus.py
```

Run the API:

```bash
uvicorn src.main:app --reload
```

Docs at `http://localhost:8000/docs`.

## Streamlit UI (optional, bonus)

A minimal Streamlit frontend (`app.py`) sits in front of the FastAPI backend —
chat-style Q&A, source citations, retry/query-type badges, a sidebar to
browse indexed documents, upload new ones, and thumbs up/down feedback.

With the API already running in one terminal, start the UI in a second one
(same venv):

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. The API base URL is editable in the
sidebar in case the backend isn't on `localhost:8000`.

## Example Requests

**Query**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I share a dependency across multiple routes?"}'
```

```json
{
  "question": "How do I share a dependency across multiple routes?",
  "answer": "Define the dependency as a plain function... [source: 03_dependency_injection.md]",
  "sources": ["03_dependency_injection.md"],
  "query_type": "how-to",
  "retries_used": 0,
  "gave_up": false
}
```

**Ingest** (upload new files)

```bash
curl -X POST http://localhost:8000/ingest \
  -F "files=@my_new_doc.md"
```

**List indexed documents**

```bash
curl http://localhost:8000/documents
```

**Feedback**

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"question": "...", "answer": "...", "rating": "up", "comment": "accurate"}'
```

## Testing

```bash
python tests/test_routing.py
```

This covers the retry/routing logic (the core evaluation criterion) with a
mocked LLM, so it runs with **no API key**. Full end-to-end `/query` calls do
need a Groq/OpenAI key.

## Design Decisions & Tradeoffs

- **Groq as default LLM**: fastest free option for a 2-day assignment; the
  provider is swappable in one file (`src/llm.py`) without touching graph or
  node logic.
- **Per-chunk grading, not batch grading**: one LLM call per retrieved chunk
  (top_k=4 by default) is simpler and more reliable to parse than asking the
  LLM to grade a batch and return structured JSON for N items, at the cost of
  more LLM calls. Worth revisiting with a larger `k` or under stricter
  latency budgets.
- **Retry limit defaults to 2** (`MAX_RETRIES` in `.env`), to bound latency —
  each retry re-runs analyze_query + retrieve + grade_documents.
- **No conversation memory / no hallucination check / no web-search
  fallback** implemented — out of scope given the 2-day window; the graph is
  structured so each would be an additional node with minimal changes
  (see "What I'd improve" below).

## What I'd Improve With More Time

- **Hallucination check**: an extra node after `generate` that asks the LLM
  whether every claim in the answer is supported by `graded_documents`,
  looping back to `generate` (with a stricter prompt) or to `fallback` if not.
- **Web search fallback**: if `grade_documents` finds nothing relevant after
  `max_retries`, call Tavily/Serper instead of going straight to `fallback`.
- **Conversation memory**: thread a `chat_history` field through `RAGState`
  and use LangGraph's checkpointer (keyed by a session id) so `/query` can
  accept follow-ups.
- **Batch grading** with structured output to cut LLM calls per query.
- **Reranking** (e.g. a cross-encoder) between retrieval and grading to
  improve precision before the grading LLM call.

## Assumptions

- A "document" for ingestion is Markdown or plain text; PDF/HTML ingestion
  is not implemented but `src/ingest.py` is the single place to extend it.
- Single-tenant, single-collection vector store — no per-user isolation.
- `/ingest` without files re-ingests the local `data/docs/` directory
  (bootstrap path); URL fetching is left as a documented extension point
  rather than implemented, to keep the assignment's 2-day scope realistic.
