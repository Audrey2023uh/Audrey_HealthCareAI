"""Project paths and runtime settings.

OpenRouter (Streamlit Secrets / env) is preferred:
  OPENROUTER_API_KEY
  OPENROUTER_MODEL   (default: openrouter/free)

Never log or print secret values.
Do not read st.secrets at module import time.
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
try:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

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
    "your-openrouter-key",
    "paste-your-openrouter-key-here",
    "paste-your-key-here",
    "configured in Streamlit Secrets",
}

_API_KEY_NAMES = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_KEY",
    "OR_API_KEY",
)
_MODEL_NAMES = (
    "OPENROUTER_MODEL",
    "OPENAI_MODEL",
)
_BASE_URL_NAMES = (
    "OPENROUTER_BASE_URL",
    "OPENAI_BASE_URL",
)


def _looks_like_real_key(value: str) -> bool:
    v = (value or "").strip()
    if not v or v in _PLACEHOLDER_KEYS:
        return False
    # Accept OpenRouter / OpenAI style keys; also any non-placeholder long token
    if v.startswith("sk-"):
        return len(v) >= 20
    return len(v) >= 16


def _from_env(names: tuple[str, ...]) -> str:
    for name in names:
        val = os.getenv(name, "").strip()
        if val:
            return val
    # Case-insensitive env scan (some hosts alter casing)
    lower_map = {k.lower(): v for k, v in os.environ.items()}
    for name in names:
        val = (lower_map.get(name.lower()) or "").strip()
        if val:
            return val
    return ""


def _secrets_obj() -> Any | None:
    """Return st.secrets when available. Safe during / after script start."""
    try:
        import streamlit as st

        return st.secrets
    except Exception:
        return None


def _from_mapping(mapping: Any, names: tuple[str, ...]) -> str:
    if mapping is None:
        return ""
    # Direct key access
    for name in names:
        try:
            if name in mapping:
                val = str(mapping[name]).strip()
                if val:
                    return val
        except Exception:
            pass
        try:
            val = str(mapping.get(name, "")).strip()  # type: ignore[attr-defined]
            if val:
                return val
        except Exception:
            pass
        try:
            val = str(getattr(mapping, name, "") or "").strip()
            if val:
                return val
        except Exception:
            pass
    # Case-insensitive key scan
    try:
        keys = list(mapping.keys())  # type: ignore[attr-defined]
    except Exception:
        keys = []
    lower_index = {str(k).lower(): k for k in keys}
    for name in names:
        real = lower_index.get(name.lower())
        if real is None:
            continue
        try:
            val = str(mapping[real]).strip()
            if val:
                return val
        except Exception:
            continue
    return ""


def _from_streamlit_secrets(names: tuple[str, ...]) -> str:
    secrets = _secrets_obj()
    if secrets is None:
        return ""
    # Flat secrets
    found = _from_mapping(secrets, names)
    if found:
        return found
    # Nested [openrouter] / [openai]
    for section in ("openrouter", "openai", "OpenRouter", "OPENROUTER"):
        try:
            sec = secrets[section]
        except Exception:
            try:
                sec = secrets.get(section)  # type: ignore[attr-defined]
            except Exception:
                sec = None
        if sec is None:
            continue
        nested_names = names + ("api_key", "key", "API_KEY", "model", "MODEL")
        found = _from_mapping(sec, nested_names)
        if found:
            return found
    return ""


def _setting(names: tuple[str, ...], default: str = "") -> str:
    env_val = _from_env(names)
    if env_val:
        return env_val
    secret_val = _from_streamlit_secrets(names)
    if secret_val:
        return secret_val
    return default


def get_openai_api_key() -> str:
    return _setting(_API_KEY_NAMES, "")


def get_openai_base_url() -> str:
    return _setting(_BASE_URL_NAMES, "") or OPENROUTER_BASE_URL


def get_openai_model() -> str:
    return _setting(_MODEL_NAMES, "") or DEFAULT_OPENROUTER_MODEL


def get_openai_embedding_model() -> str:
    return _setting(("OPENAI_EMBEDDING_MODEL",), "")


def llm_configured() -> bool:
    return _looks_like_real_key(get_openai_api_key())


def secrets_diagnostics() -> dict[str, str]:
    """Non-sensitive status for the sidebar (never includes the key)."""
    key = get_openai_api_key()
    present = _looks_like_real_key(key)
    source = "missing"
    if present:
        if _from_env(_API_KEY_NAMES):
            source = "environment"
        elif _from_streamlit_secrets(_API_KEY_NAMES):
            source = "streamlit_secrets"
        else:
            source = "detected"
    return {
        "key_status": "detected" if present else "missing",
        "key_source": source,
        "model": get_openai_model(),
        "base_url": get_openai_base_url(),
        "provider_ready": "yes" if present else "no",
    }


def provider_label_for_ui(generation_mode: str | None = None) -> str:
    if generation_mode == "openrouter_free":
        return "OpenRouter Free"
    if generation_mode == "offline_fallback":
        return "Offline Fallback"
    return "OpenRouter Free" if llm_configured() else "Offline Fallback"


# Env-only snapshots at import. Prefer getters at runtime.
OPENAI_API_KEY = _from_env(_API_KEY_NAMES)
OPENAI_BASE_URL = _from_env(_BASE_URL_NAMES) or OPENROUTER_BASE_URL
OPENAI_MODEL = _from_env(_MODEL_NAMES) or DEFAULT_OPENROUTER_MODEL
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()

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
