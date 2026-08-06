"""Project paths and runtime settings.

OpenRouter (Streamlit Secrets / env) is preferred:
  OPENROUTER_API_KEY
  OPENROUTER_MODEL   (default: openrouter/free)

Legacy OPENAI_* names remain supported as fallbacks.
Never log or print secret values.
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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"

_PLACEHOLDER_KEYS = {
    "",
    "replace-me",
    "sk-or-v1-replace-me",
    "sk-xxx",
    "your-key",
    "YOUR_KEY_HERE",
    "configured in Streamlit Secrets",
}


def _from_streamlit_secrets(name: str) -> str:
    """Read a secret from Streamlit (Cloud or local secrets.toml). Never raises."""
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

    # Nested optional sections
    for section in ("openrouter", "openai"):
        try:
            sec: Any = secrets.get(section, None)  # type: ignore[attr-defined]
        except Exception:
            sec = None
        if sec is None:
            continue
        short = name.lower().replace("openrouter_", "").replace("openai_", "")
        aliases = {
            "api_key": ("api_key", "key", "OPENROUTER_API_KEY", "OPENAI_API_KEY"),
            "model": ("model", "OPENROUTER_MODEL", "OPENAI_MODEL"),
            "base_url": ("base_url", "base", "OPENROUTER_BASE_URL", "OPENAI_BASE_URL"),
            "embedding_model": ("embedding_model", "embeddings", "OPENAI_EMBEDDING_MODEL"),
        }
        keys_to_try = aliases.get(short, (short, name))
        try:
            for k in keys_to_try:
                if k in sec:
                    return str(sec[k]).strip()
        except Exception:
            continue
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
    """API key for chat completions (OpenRouter preferred)."""
    return _setting("OPENROUTER_API_KEY") or _setting("OPENAI_API_KEY", "")


def get_openai_base_url() -> str:
    """OpenRouter-compatible base URL."""
    return (
        _setting("OPENROUTER_BASE_URL")
        or _setting("OPENAI_BASE_URL")
        or OPENROUTER_BASE_URL
    )


def get_openai_model() -> str:
    """Primary online model — defaults to openrouter/free."""
    return (
        _setting("OPENROUTER_MODEL")
        or _setting("OPENAI_MODEL")
        or DEFAULT_OPENROUTER_MODEL
    )


def get_openai_embedding_model() -> str:
    return _setting("OPENAI_EMBEDDING_MODEL", "")


def llm_configured() -> bool:
    key = get_openai_api_key()
    return bool(key) and key not in _PLACEHOLDER_KEYS


def provider_label_for_ui(generation_mode: str | None = None) -> str:
    """
    Display label:
      - OpenRouter Free when online generation is active / available
      - Offline Fallback only when fallback is actually in use (or no key)
    """
    if generation_mode == "openrouter_free":
        return "OpenRouter Free"
    if generation_mode == "offline_fallback":
        return "Offline Fallback"
    # Pre-run sidebar hint
    return "OpenRouter Free" if llm_configured() else "Offline Fallback"


# Backward-compatible module attrs (prefer getters at call time)
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
    "Research prototype only. This application is intended for educational and research purposes "
    "and does not provide medical advice. Clinical decisions remain the responsibility of "
    "qualified healthcare professionals.",
)


def refresh_openai_settings() -> None:
    global OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_EMBEDDING_MODEL
    OPENAI_API_KEY = get_openai_api_key()
    OPENAI_BASE_URL = get_openai_base_url()
    OPENAI_MODEL = get_openai_model()
    OPENAI_EMBEDDING_MODEL = get_openai_embedding_model()
