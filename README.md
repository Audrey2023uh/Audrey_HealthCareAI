# Healthcare AI — Source-Linked Evidence-Based Clinical Decision Support

**By Audrey Rah**

**Milestone 2 Engineering Prototype** — University Course Project  
**Theme:** LLMs · RAG · Agentic AI · End-to-End Application · Rapid Prototyping

> Research / education prototype only. **Not a medical device.** A licensed clinician makes the final decision.

## Live Demo & Videos

| Resource | Link |
|---|---|
| **Live Streamlit App** | [Open App](https://audrey2023uh-audrey-healthcareai-app-6w8imm.streamlit.app/) |
| **App Demo Video** | [Watch App Demo](https://drive.google.com/file/d/18PZ_HnAR45yRx9eUFE1AaSFKQB5AvJyU/view?usp=sharing) |
| **GitHub Walkthrough Video** | [Watch GitHub Walkthrough](https://drive.google.com/file/d/1oGWAk1k6g8HcmqD-Z79viZcAxNRqzTAn/view?usp=sharing) |
| **Presentation Slides** | [View / Download PowerPoint](https://github.com/Audrey2023uh/Audrey_HealthCareAI/blob/main/Milestone2_Powerpoint/Milestone2_HealthcareAI.pptx) |
| **GitHub Repository** | [Audrey_HealthCareAI](https://github.com/Audrey2023uh/Audrey_HealthCareAI) |

The app is **deployed online on Streamlit Cloud** for demonstration and access. The core RAG pipeline also supports a **local/offline fallback** (TF-IDF + FAISS + extractive generation) when an LLM/API is unavailable. Optional online LLM and live-source features require network/API access.

---

## Project summary

- Built an **end-to-end, source-linked clinical evidence assistant**: a clinician-style question is retrieved from a public medical knowledge base, answered with **inline citations**, and checked through an **8-node LangGraph** workflow.
- Delivered as a **Streamlit Cloud** demo (optional FastAPI). Core retrieval uses **local TF-IDF + FAISS**. If no LLM key is present, answers use an **extractive fallback** from retrieved chunks.
- Optional **OpenRouter / OpenAI-compatible LLM** and **live-source** checks run only when configured and the network is available. Demo eval: **citation precision = 1.00**; configured **TOP_K = 5**; retrieved chunks **4, 4, and 5**; corpus **19 documents / 20 chunks**.

Supports clinicians; **does not replace** clinical judgment.

---

## Architecture (8-node LangGraph workflow)

Implemented in `src/graph.py` as a LangGraph `StateGraph` with **exactly 8 nodes**:

```
User
 → Streamlit UI (app.py)          # also deployed on Streamlit Cloud
 → LangGraph StateGraph (src/graph.py) — 8 nodes
 → knowledge_update_agent         # optional URL probes / local supersession
 → patient_assessment_agent
 → risk_analysis_agent
 → query_agent                    # optional LLM rewrite for search
 → retrieval_agent                # FAISS + Priority 1–7 re-rank
 → verification_agent             # conflicts, citations, confidence
 → recommendation_agent           # structured recs + evidence summary
 → transparency_agent             # agent_trace + final narrative
 → Final answer with citations
```

| Node | Responsibility |
|------|----------------|
| **1. Knowledge Update** | Optional URL status / Last-Modified / ETag probes; local supersession; optional index rebuild (`src/knowledge_update.py`). Skipped unless requested. Requires network for live URL probes. |
| **2. Patient Assessment** | Merge form + text-extracted fields (age, sex, BP, diabetes, LDL, BMI, smoking, ASCVD, other CV risks). |
| **3. Clinical Risk Analysis** | Prototype risk factors, hypertension stage, obesity, diabetes risk, preventive needs. |
| **4. Query Agent** | Normalize / classify the question; optional LLM rewrite for search when an API is configured. |
| **5. Evidence Retrieval** | FAISS candidate search, Priority 1–7 re-rank, evidence context (`TOP_K` configured window). |
| **6. Evidence Verification** | Conflict flags, grounded draft (LLM or extractive), citation checks, confidence, human-review flag. |
| **7. Recommendation + Evidence Summary** | Structured recommendations with citations. |
| **8. Transparency** | Confidence, sources, hierarchy, agent trace, final clinician-facing narrative. |

**Proof of implementation:** enter a question in Streamlit → retrieved chunks, citations, agent trace, confidence, and latency.

Every answer includes retrieved chunks with scores, citation URLs, a heuristic confidence score, an agent trace, and an explicit “insufficient evidence / human review” flag when unsupported. Generation is constrained to retrieved context; missing/invalid citations are flagged.

---

## Technical stack

| Component | Choice |
|-----------|--------|
| Language | Python 3 |
| UI | Streamlit (online Cloud deploy + local `streamlit run`) |
| Orchestration | LangGraph `StateGraph` (**8 nodes**) |
| Core retrieval | FAISS (`IndexFlatIP`) + chunk metadata JSON |
| Embeddings (default) | scikit-learn **TF-IDF** (local, deterministic) |
| Embeddings (optional) | OpenAI-compatible embedding API (network/API required) |
| LLM (optional) | OpenRouter / OpenAI-compatible chat via `OPENROUTER_API_KEY` (aliases: `OPENAI_*`) |
| Offline fallback | Extractive answer from retrieved chunks (no LLM/API required) |
| API (optional) | FastAPI (`api/main.py`) + Uvicorn |
| Data | Curated public-style seed KB; optional live PubMed E-utilities (network required) |

---

## RAG pipeline

1. **Load** documents from `data/seed_medical_kb.json` (guideline summaries, MedlinePlus-style overviews, AHRQ/MedQuAD-style samples, PubMed-style abstracts).
2. **Clean** text (`src/ingest.py`).
3. **Chunk** with overlap.
4. **Embed** with **TF-IDF by default** (local).
5. **Store** vectors in `indexes/faiss.index` + `indexes/chunks.json`.
6. **Retrieve** with FAISS, then **hard-sort by clinical priority** (1 best → 7 lowest), then quality within the same priority. Semantic similarity is a secondary signal. Superseded guidelines are heavily downgraded.

**Priority 1–7:** (1) Clinical Practice Guidelines (USPSTF, ADA, AHA/ACC, NCCN, NICE, WHO, …) · (2) Systematic Reviews / Meta-Analyses · (3) Randomized Clinical Trials · (4) PubMed / PubMed Central · (5) AHRQ · (6) MedlinePlus · (7) MedQuAD (testing only).

**Query-time path:** query → embed → FAISS candidates → Priority 1–7 re-rank → context → grounded answer (optional LLM **or** extractive fallback) → citation/verification.

**Optional live PubMed:** `fetch_pubmed_abstracts(query)` in `src/ingest.py` (public NCBI E-utilities; **network required**). Bulk PMC / full MedlinePlus crawl / hospital EHR are **not** claimed as production-ready.

**Knowledge Update (prototype):** sidebar button / `scripts/run_knowledge_update.py` can probe official URLs and rebuild FAISS. Live probes need network. **Not implemented:** automatic PDF ingestion of every new society guideline into the vector DB.

---

## Evaluation

```powershell
python scripts\evaluate.py
```

Writes `outputs/eval_results.json` (latency, retrieved-chunk counts, citation precision, groundedness notes, qualitative RAG vs plain-LLM note).

**Verified demo eval set (keep these figures as reported):**

| Metric | Value |
|--------|------:|
| Citation precision | **1.00** |
| Configured TOP_K | **5** |
| Retrieved chunks (three demo queries) | **4, 4, and 5** |
| Indexed corpus | **19 documents / 20 chunks** (`indexes/meta.json`) |

`TOP_K` is the **configured** retrieval window after priority re-ranking. Actual returned counts can be lower when weak matches are filtered.

---

## Implemented vs ideal / future

**Implemented (this repo)**

- Streamlit UI, including **Streamlit Cloud** deployment for demo/access  
- LangGraph **8-node** CDSS `StateGraph`  
- FAISS RAG with citations  
- Seed medical KB ingestion  
- Local TF-IDF retrieval path  
- Extractive fallback when no LLM/API is available  
- Optional OpenAI-compatible / OpenRouter LLM (network/API required)  
- Optional FastAPI `/ask`  
- Optional PubMed abstract fetch helper (network required)  
- Evaluation script  

**Ideal / future (not implemented; not claimed as finished)**

- Full PubMed Central + MedlinePlus bulk ingestion ETL  
- Hospital EHR / FHIR integration with PHI controls  
- FDA-grade validation, clinical safety monitoring, audit logging  
- Strong neural embeddings + re-ranker + hybrid BM25  
- Human-in-the-loop clinician console with override analytics  
- Multi-tenant auth, HIPAA BAA hosting, red-team eval harness  
- Continuous guideline update watchers / automatic PDF ingestion of every new NCCN/IDSA/KDIGO release  

Per Chip Huyen–style AI engineering discipline: **do not present future items as implemented.**

---

## Engineering trade-offs

- **TF-IDF vs neural embeddings:** TF-IDF keeps local retrieval runnable without heavy torch deps; neural embeddings can improve semantic recall when an API is available.  
- **Extractive fallback vs LLM:** Guarantees a demo without keys; LLM improves fluency but must stay citation-bound and needs network/API.  
- **Seed KB vs live crawl:** Curated summaries are controllable for class demos; live crawl adds freshness plus noise/legal complexity and needs network.  
- **LangGraph vs a single chain:** Clear agent boundaries and traces for the course rubric; slightly more code than one linear RAG call.  
- **Streamlit Cloud vs local run:** Cloud is for demonstration/access; the same app also runs locally, with extractive fallback if the LLM is unavailable.

---

## Challenges & learnings

- Dependency fragility (e.g., sentence-transformers / torch stacks) → default embeddings to local TF-IDF.  
- Citation integrity must be **checked**, not assumed.  
- Medical prototypes need loud **disclaimers** and review flags.  
- Separating **implemented** vs **ideal** architecture is itself an engineering deliverable.  
- Online deploy, local retrieval, and optional APIs are distinct modes and should be described separately.

---

## How to run locally

```powershell
git clone https://github.com/Audrey2023uh/Audrey_HealthCareAI.git
cd Audrey_HealthCareAI
python -m pip install -r requirements.txt
python scripts\build_index.py
python scripts\run_demo.py --ask "What A1C target is commonly used for nonpregnant adults with type 2 diabetes?"
streamlit run app.py
```

On macOS/Linux, use `python scripts/build_index.py` (forward slashes).  
Windows shortcut: double-click `START_DEMO.bat` (installs deps, builds index, launches Streamlit).

**Local demo checklist**

1. `python scripts\build_index.py`  
2. `streamlit run app.py`  
3. Ask: *“What A1C target is commonly used for nonpregnant adults with type 2 diabetes?”*  
4. Show: Final answer → Retrieved evidence → Citations → Agent trace → metrics  

CLI alternative:

```powershell
python scripts\run_demo.py --ask "When should adults be screened for hypertension according to USPSTF?" --compare-plain
```

Optional API:

```powershell
uvicorn api.main:app --reload --app-dir .
```

### Optional local LLM configuration

Copy `.env.example` → `.env` (never commit `.env`).

**Preferred (matches Streamlit Secrets and `src/config.py`):**

```env
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=openrouter/free
```

**Legacy aliases also accepted:** `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.

Without a real API key, the system still runs using **retrieved chunks + extractive summary** (offline fallback). Optional retrieval window:

```env
TOP_K=5
```

---

## Project structure

```
Audrey_HealthCareAI/
  app.py                 # Streamlit UI
  api/main.py            # Optional FastAPI
  data/seed_medical_kb.json
  indexes/               # FAISS + chunks (generated / checked in)
  scripts/build_index.py
  scripts/run_demo.py
  scripts/evaluate.py
  src/config.py
  src/ingest.py
  src/embeddings.py
  src/vectorstore.py
  src/llm.py
  src/graph.py           # LangGraph 8-node StateGraph
  requirements.txt
  .env.example
  README.md
  Milestone2_HealthcareAI_V2.pptx
```

Use this repo to cover: resume-style summary, stack, data/architecture, trade-offs, challenges, learnings, and a **live Streamlit** flow. Reference: proposal *AI Assistant for Doctors* + Milestone 1 narrative; this implementation is the Milestone 2 proof.

---

## Troubleshooting / Streamlit configuration

**Streamlit Cloud API keys (required for optional LLM mode — never commit keys to GitHub):**

1. Open the live app  
2. Click **Manage app** (bottom-right)  
3. Click **⋮** → **Settings** → **Secrets**  
4. Paste:

```toml
OPENROUTER_API_KEY = "your-openrouter-key"
OPENROUTER_MODEL = "openrouter/free"
```

5. **Save** → **Reboot app**

Sidebar **LLM** shows **OpenRouter Free** when the online model is used, and **Offline Fallback** only when extractive fallback is used.

**If the app stays on “Your app is in the oven”:**

1. Open the app → **Manage app** → **⋮** → **Settings**  
2. Set **Python version** to **3.11** (not 3.13/3.14)  
3. **Save** → **Reboot app**  
4. Wait 3–5 minutes
