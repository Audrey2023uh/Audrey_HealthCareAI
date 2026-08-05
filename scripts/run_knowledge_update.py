"""Run the Knowledge Update Agent (URL probes + local supersession + optional rebuild)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.knowledge_update import run_knowledge_update


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Force FAISS rebuild after checks")
    args = parser.parse_args()
    report = run_knowledge_update(rebuild_index=args.rebuild)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
