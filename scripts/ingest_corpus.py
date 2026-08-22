"""Standalone script: run `python scripts/ingest_corpus.py` to (re)index data/docs/."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingest import ingest_directory

if __name__ == "__main__":
    result = ingest_directory()
    print(f"Ingested {len(result['ingested_files'])} files, {result['chunks_added']} chunks:")
    for f in result["ingested_files"]:
        print(f"  - {f}")
