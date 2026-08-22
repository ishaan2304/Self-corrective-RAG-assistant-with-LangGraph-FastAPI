"""State schema shared across all LangGraph nodes.

Kept as a single flat TypedDict since the graph is linear-with-a-loop and
every node only needs to read/write a handful of these keys. Splitting it
into nested models would add indirection without buying anything here.
"""
from typing import TypedDict, List, Optional


class RetrievedDoc(TypedDict):
    content: str
    source: str
    score: float
    relevant: Optional[bool]  # set by the grading node


class RAGState(TypedDict, total=False):
    # input
    question: str

    # query analysis
    rewritten_query: str
    query_type: str  # conceptual | how-to | troubleshooting | api-reference

    # retrieval
    documents: List[RetrievedDoc]

    # grading (self-corrective step)
    graded_documents: List[RetrievedDoc]
    retry_count: int
    max_retries: int

    # generation
    answer: str
    sources: List[str]
    gave_up: bool  # True if we exhausted retries with no relevant docs
