"""Central configuration, loaded from environment variables (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM provider ---
# "groq" (default, generous free tier) or "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama-3.1-8b-instant" if LLM_PROVIDER == "groq" else "gpt-4o-mini",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Embeddings (local, free, no API key needed) ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# --- Vector store ---
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "tech_docs")

# --- Retrieval / workflow ---
TOP_K = int(os.getenv("TOP_K", 4))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))

# --- Corpus ---
DOCS_DIR = os.getenv("DOCS_DIR", "./data/docs")

# --- Feedback log ---
FEEDBACK_LOG = os.getenv("FEEDBACK_LOG", "./data/feedback.jsonl")
