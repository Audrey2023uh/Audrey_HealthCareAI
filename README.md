# Healthcare AI — Source-Linked Evidence-Based Clinical Decision Support

**Milestone 2 engineering prototype** (university course project)  
**Theme:** LLMs · RAG · Agentic AI · End-to-end application · Rapid prototyping

> Research / education prototype only. **Not a medical device.** A licensed clinician makes the final decision.

## Live demo

**Open the app:** [https://audrey2023uh-audrey-healthcareai-app-6w8imm.streamlit.app/](https://audrey2023uh-audrey-healthcareai-app-6w8imm.streamlit.app/)

### Streamlit Cloud API keys (required for LLM mode)

**Where to paste secrets (never commit keys to GitHub):**

1. Open your live app  
2. Click **Manage app** (bottom-right)  
3. Click **⋮** → **Settings** → **Secrets**  
4. Paste:

```toml
OPENROUTER_API_KEY = "your-openrouter-key"
OPENROUTER_MODEL = "openrouter/free"
```

5. **Save** → **Reboot app**

**Important — if the app stays on “Your app is in the oven”:**

1. Open the app → **Manage app** → **⋮** → **Settings**
2. Set **Python version** to **3.11** (not 3.13/3.14)
3. **Save** → **Reboot app**
4. Wait 3–5 minutes

Sidebar **LLM** shows **OpenRouter Free** when the online model is used, and **Offline Fallback** only when extractive fallback is used.

---

## Resume-style project summary

Built an **end-to-end, source-linked clinical evidence assistant** that takes a clinician-style question, retrieves relevant public medical knowledge via **FAISS**, generates a grounded answer with **inline citations**, and verifies citation integrity through a **LangGraph multi-agent** workflow. Delivered as a runnable **Streamlit** app (optional FastAPI) that works **offline** with TF-IDF embeddings and an extractive fallback, or with an OpenAI-compatible LLM when an API key is present.

---

## Quick start

```powershell
cd "C:\Users\audre\OneDrive\1- Final project\AI HEALTH CARE"
python -m pip install -r requirements.txt
python scripts\build_index.py
python scripts\run_demo.py --ask "What A1C target is commonly used for nonpregnant adults with type 2 diabetes?"
streamlit run app.py
```

Optional API:

```powershell
uvicorn api.main:app --reload --app-dir .
```

Optional LLM (copy `.env.example` → `.env` and set `OPENAI_API_KEY`). Without a key, the system still runs using **retrieved chunks + extractive summary**.

---

## Clinical Decision Support (CDSS) workflow (implemented)

The LangGraph pipeline now runs a **7-step CDSS** loop:

1. **Patient Assessment** — age, sex, BP, diabetes, LDL, BMI, smoking, ASCVD, other CV risks (form + text extraction)  
2. **Clinical Risk Analysis** — risk factors, obesity, hypertension stage, diabetes risk, preventive needs  
3. **Evidence Retrieval** — priority hierarchy (guidelines → … → MedQuAD), prefer active guideline versions  
4. **Evidence Verification** — cross-source agreement/conflict flags  
5. **Clinical Recommendation** — lifestyle, medication, screening, follow-up, preventive strategies  
6. **Evidence Summary** — guideline name, organization, year, evidence level, citation per recommendation  
7. **Transparency** — confidence, sources consulted, hierarchy, agent trace  

Supports clinicians; **does not replace** clinical judgment.

---

Retrieved evidence is **sorted hard by priority** (1 best → 7 lowest), then by quality within the same priority:

1. Clinical Practice Guidelines (USPSTF, ADA, AHA/ACC, NCCN, NICE, WHO, …)  
2. Systematic Reviews / Meta-Analyses  
3. Randomized Clinical Trials  
4. PubMed / PubMed Central  
5. AHRQ  
6. MedlinePlus  
7. MedQuAD (testing only)

Semantic similarity is only a secondary signal. Superseded guidelines are heavily downgraded.

### Knowledge Update Agent (implemented prototype)

- `src/knowledge_update.py` + sidebar button / `scripts/run_knowledge_update.py`
- Probes official URLs (USPSTF, ADA, ACC/AHA, MedlinePlus, AHRQ, PMC)
- Tracks Last-Modified / ETag when available
- Applies local `superseded_by` rules and can rebuild FAISS

**Future (not claimed as complete):** automatic PDF ingestion of every new NCCN/IDSA/KDIGO/… release into the vector DB.

---

```
User
 → Streamlit UI (app.py)
 → LangGraph Orchestrator (src/graph.py)
 → Query Agent          # clean / classify / optional rewrite
 → Retrieval Agent      # FAISS top-k semantic search
 → Summary Agent        # LLM or extractive grounded answer
 → Verification Agent   # citation checks + confidence + review flag
 → Final Answer with Citations
```

**Proof of implementation:** enter a question in Streamlit → see retrieved chunks, citations, agent trace, confidence, and latency metrics.

---

## Technical stack (implemented)

| Component | Choice |
|-----------|--------|
| Language | Python 3 |
| UI | Streamlit |
| Orchestration | LangGraph `StateGraph` |
| RAG / vectors | FAISS (`IndexFlatIP`) + chunk metadata JSON |
| Embeddings (default) | scikit-learn **TF-IDF** (offline, deterministic) |
| Embeddings (optional) | OpenAI-compatible embedding API |
| LLM (optional) | OpenAI / OpenRouter / Ollama via `OPENAI_BASE_URL` |
| LLM (fallback) | Extractive answer from retrieved chunks |
| API (optional) | FastAPI (`api/main.py`) |
| Data | Curated public-style seed KB + optional live PubMed E-utilities |

---

## Data pipeline (implemented)

1. **Load** documents from `data/seed_medical_kb.json` (guideline summaries, MedlinePlus-style overviews, AHRQ/MedQuAD-style samples, PubMed-style abstracts).
2. **Clean** text (`src/ingest.py`).
3. **Chunk** with overlap.
4. **Embed** (TF-IDF by default).
5. **Store** vectors in `indexes/faiss.index` + `indexes/chunks.json`.

**Optional live PubMed:** `fetch_pubmed_abstracts(query)` in `src/ingest.py` (public NCBI E-utilities). Bulk PMC / full MedlinePlus crawl / hospital EHR are **not** claimed as production-ready in this prototype.

### Source types in seed KB

- Clinical guideline summaries (USPSTF, ADA, ACC/AHA themes)
- MedlinePlus-style public pages
- AHRQ shared decision-making themes
- MedQuAD-style Q/A sample
- PubMed-style educational abstracts

---

## Multi-agent responsibilities

| Agent | Responsibility |
|-------|----------------|
| **Query Agent** | Normalize question, light clinical typing, optional LLM rewrite for search |
| **Retrieval Agent** | Vector search, top-k, build evidence context block |
| **Summary Agent** | Grounded answer with `[n]` citations (LLM or extractive) |
| **Verification Agent** | Check citation indices, retrieval scores, confidence, human-review flag |

---

## Explainability (every answer)

- Retrieved documents / chunks with scores  
- Citation list with URLs  
- Confidence score (heuristic ± optional LLM verdict)  
- Agent trace  
- Explicit “insufficient evidence / human review” when unsupported  

The system **avoids unsupported answers** by constraining generation to retrieved context and flagging missing/invalid citations.

---

## Evaluation

```powershell
python scripts\evaluate.py
```

Writes `outputs/eval_results.json` with:

- retrieval / response latency  
- number of retrieved chunks  
- citation precision (valid `[n]` vs hit list)  
- groundedness notes  
- qualitative RAG vs plain-LLM comparison note  

---

## Implemented vs ideal future architecture

### Implemented (works in this repo)

- Streamlit demo UI  
- LangGraph 4-agent pipeline  
- FAISS RAG with citations  
- Seed medical KB ingestion  
- Offline TF-IDF path  
- Optional OpenAI-compatible LLM  
- Optional FastAPI `/ask`  
- Optional PubMed abstract fetch helper  
- Evaluation script  

### Ideal / future (not claimed as finished product)

- Full PubMed Central + MedlinePlus bulk ingestion ETL  
- Hospital EHR / FHIR integration with PHI controls  
- FDA-grade validation, clinical safety monitoring, audit logging  
- Strong neural embeddings + re-ranker + hybrid BM25  
- Human-in-the-loop clinician console with override analytics  
- Multi-tenant auth, HIPAA BAA hosting, red-team eval harness  
- Continuous guideline update watchers  

Per Chip Huyen–style AI engineering discipline: **do not present future items as implemented.**

---

## Engineering trade-offs

- **TF-IDF vs neural embeddings:** TF-IDF keeps the demo always runnable without heavy torch deps; neural embeddings improve semantic recall when an API is available.  
- **Extractive fallback vs LLM:** Guarantees a demo without keys; LLM improves fluency but must stay citation-bound.  
- **Seed KB vs live crawl:** Curated summaries are controllable for class demos; live crawl adds freshness and noise/legal complexity.  
- **LangGraph vs single chain:** Clear agent boundaries and traces for the course rubric; slightly more code than a linear RAG call.

---

## Challenges & lessons learned

- Dependency fragility (e.g., sentence-transformers / torch stacks) → default to offline embeddings.  
- Citation integrity must be **checked**, not assumed.  
- Medical prototypes require loud **disclaimers** and review flags.  
- Separating **implemented** vs **ideal** architecture is itself an engineering deliverable.

---

## Live demo checklist

1. `python scripts\build_index.py`  
2. `streamlit run app.py`  
3. Ask: *“What A1C target is commonly used for nonpregnant adults with type 2 diabetes?”*  
4. Show: Final answer → Retrieved evidence → Citations → Agent trace → metrics  

CLI alternative:

```powershell
python scripts\run_demo.py --ask "When should adults be screened for hypertension according to USPSTF?" --compare-plain
```

---

## Project layout

```
AI HEALTH CARE/
  app.py                 # Streamlit UI
  api/main.py            # Optional FastAPI
  data/seed_medical_kb.json
  indexes/               # FAISS + chunks (generated)
  scripts/build_index.py
  scripts/run_demo.py
  scripts/evaluate.py
  src/config.py
  src/ingest.py
  src/embeddings.py
  src/vectorstore.py
  src/llm.py
  src/graph.py           # LangGraph agents
  requirements.txt
  .env.example
  README.md
```

---

## Milestone 2 presentation alignment

Use this repo to speak to:

1. Resume-style summary (section above)  
2. Detailed AI tech stack (table)  
3. Data, model, architecture (pipeline diagram)  
4. Engineering trade-offs  
5. Challenges  
6. Lessons learned  
7. **Live demo** of working Streamlit flow  

Reference: proposal *AI Assistant for Doctors* + Milestone 1 presentation narrative; implementation is the Milestone 2 proof.
