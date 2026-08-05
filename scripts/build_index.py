"""Build FAISS index from seed medical knowledge base."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vectorstore import VectorStore


def main() -> None:
    store = VectorStore()
    meta = store.build_from_seed(force=True)
    print(json.dumps(meta, indent=2))
    print(f"Wrote indexes/faiss.index and indexes/chunks.json ({meta['n_chunks']} chunks)")


if __name__ == "__main__":
    main()
