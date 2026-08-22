"""The four LangGraph nodes: analyze_query, retrieve, grade_documents, generate.

Design note on retries: grade_documents is the only place that increments
retry_count. It increments it exactly when this attempt found zero relevant
docs, which is also the signal route_after_grading uses to decide whether to
loop back to analyze_query (rewrite) or give up. Keeping the counter's only
writer next to the condition that reads it keeps the retry logic in one
place instead of split across two nodes.
"""
import json
from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm
from src.vectorstore import similarity_search
from src import config


QUERY_ANALYSIS_PROMPT = """You rewrite user questions to improve retrieval from a \
technical documentation vector store about FastAPI.

Given the user's question{retry_note}, produce a JSON object with exactly these keys:
- "rewritten_query": a clearer, more specific version of the question, expanded with \
relevant synonyms/terms a doc would use (e.g. "auth" -> "authentication dependency"). \
Keep it a single search-friendly sentence, not a list.
- "query_type": one of "conceptual", "how-to", "troubleshooting", "api-reference"

Respond with ONLY the JSON object, no other text.

Question: {question}"""

GRADING_PROMPT = """You grade whether a retrieved document chunk is relevant to a \
user's question. Answer with only one word: "relevant" or "irrelevant".

Question: {question}

Document chunk:
\"\"\"{content}\"\"\""""

GENERATION_PROMPT = """You are a technical documentation assistant. Answer the \
question using ONLY the provided context. If the context does not fully answer \
the question, say what is missing. Cite sources inline like [source: filename].

Question: {question}

Context:
{context}

Answer:"""


def _parse_json_loose(text: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences; strip that before parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def analyze_query(state: dict) -> dict:
    retry_note = ""
    if state.get("retry_count", 0) > 0:
        retry_note = (
            f" (a previous search for '{state.get('rewritten_query', state['question'])}' "
            "found no relevant documents — try different phrasing or broader terms)"
        )
    llm = get_llm()
    prompt = QUERY_ANALYSIS_PROMPT.format(retry_note=retry_note, question=state["question"])
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        parsed = _parse_json_loose(response.content)
        rewritten = parsed.get("rewritten_query", state["question"])
        query_type = parsed.get("query_type", "conceptual")
    except (json.JSONDecodeError, AttributeError):
        # Fall back to the raw question if the LLM didn't return clean JSON.
        rewritten, query_type = state["question"], "conceptual"

    return {"rewritten_query": rewritten, "query_type": query_type}


def retrieve(state: dict) -> dict:
    query = state.get("rewritten_query") or state["question"]
    results = similarity_search(query, k=config.TOP_K)
    documents = [{"content": r["content"], "source": r["source"], "score": r["score"], "relevant": None} for r in results]
    return {"documents": documents}


def grade_documents(state: dict) -> dict:
    llm = get_llm()
    question = state["question"]
    graded = []
    for doc in state.get("documents", []):
        prompt = GRADING_PROMPT.format(question=question, content=doc["content"])
        verdict = llm.invoke([HumanMessage(content=prompt)]).content.strip().lower()
        is_relevant = verdict.startswith("relevant")
        graded.append({**doc, "relevant": is_relevant})

    relevant_docs = [d for d in graded if d["relevant"]]

    update = {"documents": graded, "graded_documents": relevant_docs}
    if not relevant_docs:
        # This attempt failed — bump the retry counter so the router can decide
        # whether to loop back (rewrite) or give up.
        update["retry_count"] = state.get("retry_count", 0) + 1
    return update


def generate(state: dict) -> dict:
    llm = get_llm()
    docs = state.get("graded_documents", [])
    context = "\n\n".join(f"[source: {d['source']}]\n{d['content']}" for d in docs)
    prompt = GENERATION_PROMPT.format(question=state["question"], context=context)
    response = llm.invoke([SystemMessage(content="Be concise and accurate."), HumanMessage(content=prompt)])
    sources = sorted({d["source"] for d in docs})
    return {"answer": response.content.strip(), "sources": sources, "gave_up": False}


def fallback(state: dict) -> dict:
    return {
        "answer": (
            "I don't have enough relevant information in the indexed documentation "
            "to answer that confidently. Try rephrasing, or ingest documents that "
            "cover this topic."
        ),
        "sources": [],
        "gave_up": True,
    }
