"""Ingestion pipeline: load -> chunk -> embed -> store.

Chunking strategy
------------------
We use LangChain's MarkdownHeaderTextSplitter followed by a
RecursiveCharacterTextSplitter (chunk_size=800, overlap=120):

- The Markdown header split first breaks each doc at "## " boundaries, so a
  chunk never straddles two unrelated subsections (e.g. "Order Matters" and
  "Predefined Values with Enums" never end up in the same chunk). Each
  resulting section keeps its header text as context.
- Sections are then recursively split further only if they exceed 800
  characters, with a 120-character overlap so a sentence that explains a
  code block right at a cut point isn't orphaned from the code above it.
- 800 chars (~150-200 tokens) is small enough to keep retrieval precise
  (a chunk is about one concept) but large enough to keep a code snippet
  and the paragraph explaining it together, which matters for technical
  docs more than for prose.
"""
import glob
import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from src import config
from src.vectorstore import get_vectorstore

HEADER_SPLITTER = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "section")])
CHUNK_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)


def load_markdown_files(docs_dir: str) -> list[tuple[str, str]]:
    """Return [(filename, raw_text), ...] for every .md file in docs_dir."""
    paths = sorted(glob.glob(os.path.join(docs_dir, "*.md")))
    return [(os.path.basename(p), open(p, encoding="utf-8").read()) for p in paths]


def chunk_document(filename: str, text: str) -> list[dict]:
    header_sections = HEADER_SPLITTER.split_text(text)
    chunks = []
    for section in header_sections:
        for piece in CHUNK_SPLITTER.split_text(section.page_content):
            chunks.append({"text": piece, "source": filename, "section": section.metadata.get("section", "")})
    return chunks


def ingest_directory(docs_dir: str = config.DOCS_DIR) -> dict:
    """Load every markdown file in docs_dir, chunk it, and add it to Chroma."""
    files = load_markdown_files(docs_dir)
    if not files:
        return {"ingested_files": [], "chunks_added": 0}

    store = get_vectorstore()
    texts, metadatas = [], []
    for filename, text in files:
        for chunk in chunk_document(filename, text):
            texts.append(chunk["text"])
            metadatas.append({"source": chunk["source"], "section": chunk["section"]})

    if texts:
        store.add_texts(texts=texts, metadatas=metadatas)

    return {"ingested_files": [f for f, _ in files], "chunks_added": len(texts)}


def ingest_text(filename: str, text: str) -> dict:
    """Chunk and index a single in-memory document (used by /ingest uploads)."""
    store = get_vectorstore()
    chunks = chunk_document(filename, text)
    if chunks:
        store.add_texts(
            texts=[c["text"] for c in chunks],
            metadatas=[{"source": c["source"], "section": c["section"]} for c in chunks],
        )
    return {"ingested_files": [filename], "chunks_added": len(chunks)}


if __name__ == "__main__":
    result = ingest_directory()
    print(f"Ingested {len(result['ingested_files'])} files, {result['chunks_added']} chunks.")
    for f in result["ingested_files"]:
        print(f"  - {f}")
