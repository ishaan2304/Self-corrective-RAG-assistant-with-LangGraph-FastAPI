"""FastAPI app: /query, /ingest, /documents, /feedback."""
import json
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src import config
from src.graph import run_query
from src.ingest import ingest_directory, ingest_text
from src.vectorstore import list_sources

app = FastAPI(
    title="Technical Documentation Assistant",
    description="Self-corrective RAG over technical docs, built with LangGraph.",
    version="1.0.0",
)


# ---------- schemas ----------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["How do I inject a shared dependency?"])


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    query_type: Optional[str] = None
    retries_used: int = 0
    gave_up: bool = False


class IngestUrlRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    ingested_files: list[str]
    chunks_added: int


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: str = Field(..., pattern="^(up|down)$")
    comment: Optional[str] = None


# ---------- endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")
    try:
        result = run_query(req.question)
    except RuntimeError as e:
        # e.g. missing API key
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(
        question=req.question,
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        query_type=result.get("query_type"),
        retries_used=result.get("retry_count", 0),
        gave_up=result.get("gave_up", False),
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(default=None)):
    """Ingest new documents. Accepts uploaded .md/.txt files.

    If no files are provided, re-ingests everything currently in the local
    DOCS_DIR (useful for a first-run / bootstrap call).
    """
    if not files:
        result = ingest_directory()
        return IngestResponse(**result)

    total_files, total_chunks = [], 0
    for f in files:
        if not f.filename.lower().endswith((".md", ".txt")):
            raise HTTPException(status_code=422, detail=f"unsupported file type: {f.filename}")
        content = (await f.read()).decode("utf-8", errors="ignore")
        result = ingest_text(f.filename, content)
        total_files.extend(result["ingested_files"])
        total_chunks += result["chunks_added"]

    return IngestResponse(ingested_files=total_files, chunks_added=total_chunks)


@app.get("/documents")
def documents():
    return {"indexed_sources": list_sources()}


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    os.makedirs(os.path.dirname(config.FEEDBACK_LOG), exist_ok=True)
    entry = {"timestamp": time.time(), **req.model_dump()}
    with open(config.FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "recorded"}
