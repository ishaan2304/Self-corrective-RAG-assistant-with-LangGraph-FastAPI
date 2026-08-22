"""Chroma vector store wrapper.

Embeddings run locally via sentence-transformers (all-MiniLM-L6-v2, 384-dim,
~80MB) so ingestion and retrieval need zero API keys and zero cost. Only the
grading/generation LLM calls need a key.
"""
from functools import lru_cache
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src import config


@lru_cache
def get_embeddings():
    return HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)


@lru_cache
def get_vectorstore():
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=config.CHROMA_DIR,
    )


def list_sources() -> list[str]:
    """Return the distinct source filenames currently indexed."""
    store = get_vectorstore()
    data = store.get(include=["metadatas"])
    sources = {m.get("source", "unknown") for m in data.get("metadatas", [])}
    return sorted(sources)


def similarity_search(query: str, k: int):
    store = get_vectorstore()
    results = store.similarity_search_with_relevance_scores(query, k=k)
    return [
        {"content": doc.page_content, "source": doc.metadata.get("source", "unknown"), "score": score}
        for doc, score in results
    ]
