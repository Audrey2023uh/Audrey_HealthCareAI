"""Document loading, cleaning, chunking — preserves evidence-tier metadata."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.config import CHUNK_OVERLAP, CHUNK_SIZE, SEED_KB
from src.evidence_rank import annotate_missing_metadata, infer_tier


@dataclass
class Document:
    doc_id: str
    title: str
    source_type: str
    organization: str
    url: str
    year: int | str
    text: str
    evidence_tier: int = 4
    evidence_level: str = "unknown"
    recommendation_strength: str = "unknown"
    superseded: bool = False
    superseded_by: str = ""
    supersedes: str = ""
    status: str = "active"
    topic_key: str = ""
    study_design: str = ""
    journal_quality: str = ""
    citation_impact: float | None = None
    source_credibility: float | None = None
    published_year: int | str = ""


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source_type: str
    organization: str
    url: str
    year: int | str
    text: str
    chunk_index: int
    evidence_tier: int = 4
    evidence_level: str = "unknown"
    recommendation_strength: str = "unknown"
    superseded: bool = False
    superseded_by: str = ""
    status: str = "active"
    topic_key: str = ""
    study_design: str = ""
    journal_quality: str = ""
    citation_impact: float | None = None
    source_credibility: float | None = None
    published_year: int | str = ""


def clean_text(text: str) -> str:
    text = text.replace("\u0000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = clean_text(text)
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        window = text[start:end]
        if end < len(text):
            cut = window.rfind(". ", max(0, len(window) - 120))
            if cut > chunk_size // 3:
                end = start + cut + 1
                window = text[start:end]
        chunks.append(window.strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def load_seed_documents(path: Path = SEED_KB) -> list[Document]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    docs: list[Document] = []
    for item in raw:
        meta = annotate_missing_metadata(item)
        year = meta.get("year") or meta.get("published_year") or ""
        docs.append(
            Document(
                doc_id=meta["doc_id"],
                title=meta["title"],
                source_type=meta["source_type"],
                organization=meta["organization"],
                url=meta["url"],
                year=year,
                text=clean_text(meta["text"]),
                evidence_tier=int(meta.get("evidence_tier") or infer_tier(meta)),
                evidence_level=str(meta.get("evidence_level") or "unknown"),
                recommendation_strength=str(meta.get("recommendation_strength") or "unknown"),
                superseded=bool(meta.get("superseded")),
                superseded_by=str(meta.get("superseded_by") or ""),
                supersedes=str(meta.get("supersedes") or ""),
                status=str(meta.get("status") or ("superseded" if meta.get("superseded") else "active")),
                topic_key=str(meta.get("topic_key") or ""),
                study_design=str(meta.get("study_design") or ""),
                journal_quality=str(meta.get("journal_quality") or ""),
                citation_impact=meta.get("citation_impact"),
                source_credibility=meta.get("source_credibility"),
                published_year=meta.get("published_year") or year,
            )
        )
    return docs


def documents_to_chunks(docs: list[Document]) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        parts = chunk_text(doc.text)
        for i, part in enumerate(parts):
            out.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}::c{i}",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    source_type=doc.source_type,
                    organization=doc.organization,
                    url=doc.url,
                    year=doc.year,
                    text=part,
                    chunk_index=i,
                    evidence_tier=doc.evidence_tier,
                    evidence_level=doc.evidence_level,
                    recommendation_strength=doc.recommendation_strength,
                    superseded=doc.superseded,
                    superseded_by=doc.superseded_by,
                    status=doc.status,
                    topic_key=doc.topic_key,
                    study_design=doc.study_design,
                    journal_quality=doc.journal_quality,
                    citation_impact=doc.citation_impact,
                    source_credibility=doc.source_credibility,
                    published_year=doc.published_year,
                )
            )
    return out


def chunks_to_dicts(chunks: list[Chunk]) -> list[dict[str, Any]]:
    return [asdict(c) for c in chunks]


def fetch_pubmed_abstracts(query: str, retmax: int = 3) -> list[Document]:
    """Optional live PubMed E-utilities fetch (public API, no key required)."""
    import xml.etree.ElementTree as ET

    import requests

    try:
        esearch = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"},
            timeout=20,
        )
        esearch.raise_for_status()
        ids = esearch.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        efetch = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
            timeout=30,
        )
        efetch.raise_for_status()
        root = ET.fromstring(efetch.text)
        docs: list[Document] = []
        for art in root.findall(".//PubmedArticle"):
            pmid = (art.findtext(".//PMID") or "unknown").strip()
            title = (art.findtext(".//ArticleTitle") or f"PubMed {pmid}").strip()
            abstract_bits = [t.text or "" for t in art.findall(".//Abstract/AbstractText")]
            abstract = clean_text(" ".join(abstract_bits))
            if not abstract:
                continue
            year = art.findtext(".//PubDate/Year") or ""
            docs.append(
                Document(
                    doc_id=f"PMID-{pmid}",
                    title=title,
                    source_type="pubmed",
                    organization="PubMed/NLM",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    year=year,
                    text=abstract,
                    evidence_tier=4,
                    evidence_level="observational",
                    recommendation_strength="unknown",
                    status="active",
                    study_design="peer_reviewed_abstract",
                    published_year=year,
                )
            )
        return docs
    except Exception:
        return []
