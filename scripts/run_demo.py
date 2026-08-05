"""CLI: build index + run a sample question."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph import run_pipeline
from src.vectorstore import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Healthcare AI CDSS prototype")
    parser.add_argument("--build-index", action="store_true", help="Build FAISS index from seed KB")
    parser.add_argument("--ask", type=str, default="", help="Run one clinical question through the graph")
    parser.add_argument("--compare-plain", action="store_true", help="Also print a non-RAG reminder note")
    args = parser.parse_args()

    if args.build_index or not (ROOT / "indexes" / "faiss.index").exists():
        store = VectorStore()
        meta = store.build_from_seed(force=True)
        print("Index built:", json.dumps(meta, indent=2))

    if args.ask:
        out = run_pipeline(args.ask)
        print("\n===== FINAL ANSWER =====\n")
        print(out.get("final_answer"))
        print("\n===== CITATIONS / HITS =====\n")
        for i, h in enumerate(out.get("hits") or [], 1):
            print(f"[{i}] {h.get('doc_id')} | {h.get('title')}")
            print(f"    {h.get('url')}")
            print(f"    score={h.get('score'):.4f}")
        print("\n===== METRICS =====\n")
        print(json.dumps({
            "confidence": out.get("confidence"),
            "needs_human_review": out.get("needs_human_review"),
            "timings": out.get("timings"),
            "agent_trace": out.get("agent_trace"),
            "verification": out.get("verification"),
        }, indent=2))
        if args.compare_plain:
            print(
                "\n[Comparison note] A plain LLM without RAG may answer fluently but "
                "without these retrieved source links. This prototype forces retrieval-first grounding."
            )


if __name__ == "__main__":
    main()
