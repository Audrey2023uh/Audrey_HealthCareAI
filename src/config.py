"""Project paths and runtime settings.

Reads OpenAI-compatible settings from (in order):
1. Environment variables
2. Streamlit Cloud secrets (`st.secrets`) — flat or `[openai]` section
3. Local `.env` (via python-dotenv)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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

_PLACEHOLDER_KEYS = {
    "",
    "replace-me",
    "sk-or-v1-replace-me",
    "sk-xxx",
    "your-key",
    "YOUR_KEY_HERE",
}


def _from_streamlit_secrets(name: str) -> str:
    """Read a secret from Streamlit (Cloud or local secrets.toml)."""
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:
        return ""

    try:
        if name in secrets:
            return str(secrets[name]).strip()
    except Exception:
        pass

    # Nested forms: [openai] OPENAI_API_KEY=...  OR  [openai] api_key=...
    try:
        openai_sec: Any = secrets.get("openai", None)  # type: ignore[attr-defined]
    except Exception:
        openai_sec = None
    if openai_sec is None:
        return ""

    short = name.replace("OPENAI_", "").lower()  # api_key, base_url, model, embedding_model
    aliases = {
        "api_key": ("api_key", "key", "OPENAI_API_KEY"),
        "base_url": ("base_url", "base", "OPENAI_BASE_URL"),
        "model": ("model", "OPENAI_MODEL"),
        "embedding_model": ("embedding_model", "embeddings", "OPENAI_EMBEDDING_MODEL"),
    }
    keys_to_try = aliases.get(short, (short, name))
    try:
        for k in keys_to_try:
            if k in openai_sec:
                return str(openai_sec[k]).strip()
    except Exception:
        return ""
    return ""


def _setting(name: str, default: str = "") -> str:
    env_val = os.getenv(name, "").strip()
    if env_val:
        return env_val
    secret_val = _from_streamlit_secrets(name)
    if secret_val:
        return secret_val
    return default


def get_openai_api_key() -> str:
    return _setting("OPENAI_API_KEY", "")


def get_openai_base_url() -> str:
    return _setting("OPENAI_BASE_URL", "https://api.openai.com/v1")


def get_openai_model() -> str:
    return _setting("OPENAI_MODEL", "gpt-4o-mini")


def get_openai_embedding_model() -> str:
    return _setting("OPENAI_EMBEDDING_MODEL", "")


# Backward-compatible names (resolved at import; refresh via getters in hot paths)
OPENAI_API_KEY = get_openai_api_key()
OPENAI_BASE_URL = get_openai_base_url()
OPENAI_MODEL = get_openai_model()
OPENAI_EMBEDDING_MODEL = get_openai_embedding_model()

TOP_K = int(os.getenv("TOP_K", "5"))
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "20"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

APP_DISCLAIMER = os.getenv(
    "APP_DISCLAIMER",
    "Research/education prototype only. Not a medical device. The clinician makes the final decision.",
)


def llm_configured() -> bool:
    key = get_openai_api_key()
    return bool(key) and key not in _PLACEHOLDER_KEYS


# Keep module attrs roughly in sync when getters are used elsewhere
def refresh_openai_settings() -> None:
    global OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_EMBEDDING_MODEL
    OPENAI_API_KEY = get_openai_api_key()
    OPENAI_BASE_URL = get_openai_base_url()
    OPENAI_MODEL = get_openai_model()
    OPENAI_EMBEDDING_MODEL = get_openai_embedding_model()
