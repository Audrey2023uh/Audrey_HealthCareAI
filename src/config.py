"""Project paths and runtime settings."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

SEED_KB = DATA_DIR / "seed_medical_kb.json"
FAISS_INDEX = INDEX_DIR / "faiss.index"
CHUNKS_JSON = INDEX_DIR / "chunks.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()

TOP_K = int(os.getenv("TOP_K", "5"))
# Retrieve a wider semantic candidate pool, then rerank by evidence tier
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "20"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

APP_DISCLAIMER = os.getenv(
    "APP_DISCLAIMER",
    "Research/education prototype only. Not a medical device. The clinician makes the final decision.",
)


def llm_configured() -> bool:
    return bool(OPENAI_API_KEY) and OPENAI_API_KEY not in {"sk-or-v1-replace-me", "replace-me", ""}
