"""
Streamlit GUI — Clinical Decision Support Evidence Assistant (Milestone 2)

Premium enterprise healthcare UI (visual only).
Backend agents / retrieval / CDSS logic are unchanged.
Run: streamlit run app.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import APP_DISCLAIMER, TOP_K, llm_configured

st.set_page_config(
    page_title="Clinical Evidence CDSS",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Premium healthcare theme (inspired by enterprise clinical dashboards)
# ---------------------------------------------------------------------------
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  --navy: #0F172A;
  --blue: #1D4ED8;
  --cyan: #22D3EE;
  --bg: #F8FAFC;
  --card: #FFFFFF;
  --border: #E2E8F0;
  --success: #16A34A;
  --warning: #F59E0B;
  --error: #DC2626;
  --text: #0F172A;
  --muted: #64748B;
  --soft: #F1F5F9;
  --shadow: 0 1px 2px rgba(15, 23, 42, 0.05), 0 10px 28px rgba(15, 23, 42, 0.06);
  --shadow-lg: 0 8px 30px rgba(15, 23, 42, 0.10);
  --radius: 16px;
}

html, body, .stApp {
  font-family: Inter, "IBM Plex Sans", "Source Sans 3", "Segoe UI", sans-serif !important;
  color: var(--text);
}
.stMarkdown, .stMarkdown p, label {
  color: #0F172A !important;
}

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(34, 211, 238, 0.12), transparent 55%),
    radial-gradient(900px 420px at 90% 0%, rgba(29, 78, 216, 0.10), transparent 50%),
    linear-gradient(180deg, #EEF2FF 0%, var(--bg) 42%, #F8FAFC 100%) !important;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
  padding-top: 20px !important;
  padding-bottom: 48px !important;
  padding-left: 28px !important;
  padding-right: 28px !important;
  max-width: 1280px;
}

/* ===== Header ===== */
.app-header {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #1D4ED8 100%);
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-lg);
  color: #fff;
}
.app-header::after {
  content: "";
  position: absolute;
  right: -40px; top: -40px;
  width: 220px; height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34,211,238,0.35), transparent 70%);
  pointer-events: none;
}
.app-header-inner { position: relative; z-index: 1; display: flex; gap: 18px; align-items: flex-start; }
.brand-mark {
  width: 52px; height: 52px; border-radius: 14px; flex-shrink: 0;
  background: linear-gradient(145deg, #22D3EE, #1D4ED8);
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 18px; color: #0F172A;
  box-shadow: 0 8px 20px rgba(34,211,238,0.25);
}
.app-header h1 {
  margin: 0; font-size: 30px; font-weight: 800; letter-spacing: -0.03em;
  color: #FFFFFF !important; line-height: 1.15;
}
.app-header .subtitle {
  margin-top: 8px; font-size: 15px; line-height: 1.55; color: #CBD5E1; max-width: 900px;
}
.pills { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; }
.pill {
  font-size: 12px; font-weight: 600; color: #E0F2FE;
  background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 999px; padding: 6px 12px;
}

.disclaimer {
  background: #FFFBEB; border: 1px solid #FDE68A; border-left: 4px solid var(--warning);
  border-radius: 14px; padding: 14px 18px; margin-bottom: 22px;
  font-size: 13.5px; color: #92400E; line-height: 1.55; font-weight: 500;
}

/* ===== Cards ===== */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 26px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.card-title {
  margin: 0 0 6px 0; font-size: 20px; font-weight: 700; color: var(--navy); letter-spacing: -0.02em;
}
.card-title.sm { font-size: 16px; font-weight: 700; }
.card-caption { margin: 0 0 16px 0; font-size: 13px; color: var(--muted); line-height: 1.5; }

/* ===== KPI ===== */
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px;
}
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } }

.kpi {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 18px 16px 18px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.kpi::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, var(--cyan), var(--blue));
}
.kpi .label {
  font-size: 11px; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.06em; padding-left: 8px;
}
.kpi .value {
  margin-top: 6px; font-size: 30px; font-weight: 800; color: var(--navy);
  letter-spacing: -0.03em; line-height: 1.1; padding-left: 8px;
}
.kpi .hint { margin-top: 6px; font-size: 12px; color: var(--muted); padding-left: 8px; }

/* ===== Evidence tiles ===== */
.ev-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 8px;
}
@media (max-width: 1100px) { .ev-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 700px) { .ev-grid { grid-template-columns: 1fr; } }

.ev-tile {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 18px 16px 18px;
  min-height: 170px;
  box-shadow: var(--shadow);
  border-top: 4px solid var(--accent, var(--blue));
}
.ev-tile.featured {
  border: 1px solid rgba(29, 78, 216, 0.35);
  border-top: 4px solid var(--blue);
  background: linear-gradient(180deg, #EFF6FF 0%, #FFFFFF 55%);
  box-shadow: 0 10px 28px rgba(29, 78, 216, 0.12);
}
.ev-tile h4 {
  margin: 0 0 10px 0; font-size: 15px; font-weight: 700; color: var(--navy);
}
.ev-tile .org { font-size: 13px; color: #334155; line-height: 1.45; font-weight: 500; }
.ev-tile .meta { margin-top: 12px; font-size: 12px; font-weight: 700; color: var(--muted); }
.ev-tile .empty { font-size: 13px; color: var(--muted); }

.source-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 16px 18px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}
.source-card.alt { background: #F8FAFC; }
.source-card .title { font-size: 15px; font-weight: 700; color: var(--navy); margin: 0 0 8px 0; }
.source-card .meta { font-size: 13px; color: var(--muted); line-height: 1.55; }
.source-card a { color: var(--blue); font-weight: 600; text-decoration: none; font-size: 13px; }
.source-card a:hover { text-decoration: underline; }

.badge {
  display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 10px;
  border-radius: 999px; margin-right: 6px; margin-bottom: 4px;
}
.badge-indexed { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.badge-cached { background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
.badge-offline { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
.badge-live { background: #ECFDF5; color: #166534; border: 1px solid #BBF7D0; }

.rec-item {
  border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px;
  margin-bottom: 10px; background: linear-gradient(180deg, #FFFFFF, #F8FAFC);
}
.rec-item .body { font-size: 14px; color: var(--text); line-height: 1.55; font-weight: 500; }
.rec-item .meta { margin-top: 8px; font-size: 12px; color: var(--muted); }

.app-footer {
  margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--border);
  text-align: center; color: var(--muted); font-size: 12px; line-height: 1.7;
}
.app-footer strong { color: var(--navy); font-weight: 700; font-size: 13px; }

/* ===== Sidebar — matches header navy→blue premium system ===== */
section[data-testid="stSidebar"] {
  background:
    radial-gradient(420px 240px at 0% 0%, rgba(34, 211, 238, 0.18), transparent 60%),
    radial-gradient(380px 260px at 100% 8%, rgba(29, 78, 216, 0.35), transparent 55%),
    linear-gradient(180deg, #0F172A 0%, #1E3A8A 48%, #1D4ED8 100%) !important;
  border-right: 1px solid rgba(34, 211, 238, 0.22);
  box-shadow: inset -1px 0 0 rgba(255,255,255,0.04);
}
section[data-testid="stSidebar"] > div:first-child {
  background: transparent !important;
  padding-top: 12px !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] .stCaption {
  color: #E2E8F0 !important;
}
section[data-testid="stSidebar"] strong { color: #FFFFFF !important; }
section[data-testid="stSidebar"] code {
  background: rgba(15, 23, 42, 0.35) !important;
  color: #A5F3FC !important;
  border: 1px solid rgba(34, 211, 238, 0.25) !important;
  border-radius: 6px !important;
  font-size: 11px !important;
}

.sidebar-shell { padding: 4px 2px 8px 2px; }
.sidebar-brand {
  display: flex; gap: 12px; align-items: center;
  padding: 10px 10px 16px 10px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}
.sidebar-brand .mark {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  background: linear-gradient(145deg, #22D3EE, #1D4ED8);
  color: #0F172A; font-weight: 800; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 16px rgba(34, 211, 238, 0.28);
}
.sidebar-brand .name {
  font-size: 15px; font-weight: 800; color: #F8FAFC !important; letter-spacing: -0.02em; line-height: 1.2;
}
.sidebar-brand .role { font-size: 11px; color: #CBD5E1 !important; margin-top: 3px; }

.sidebar-section {
  font-size: 10px; font-weight: 800; color: #A5F3FC !important;
  text-transform: uppercase; letter-spacing: 0.1em;
  margin: 16px 4px 10px 4px;
}

/* Real Streamlit radio → enterprise nav buttons */
section[data-testid="stSidebar"] div[data-testid="stRadio"] {
  margin-bottom: 4px !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
  background: transparent !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
  background: rgba(15, 23, 42, 0.32) !important;
  border: 1px solid rgba(148, 163, 184, 0.22) !important;
  border-radius: 12px !important;
  padding: 11px 14px !important;
  margin: 0 !important;
  color: #E2E8F0 !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
  background: rgba(34, 211, 238, 0.12) !important;
  border-color: rgba(34, 211, 238, 0.40) !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked),
section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"] {
  background: linear-gradient(135deg, rgba(29, 78, 216, 0.62), rgba(34, 211, 238, 0.24)) !important;
  border: 1px solid rgba(34, 211, 238, 0.70) !important;
  color: #ECFEFF !important;
  font-weight: 700 !important;
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.28), 0 8px 22px rgba(15, 23, 42, 0.28) !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label span {
  color: inherit !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] svg,
section[data-testid="stSidebar"] div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
  color: inherit !important;
}
/* Hide default radio circles for a button look */
section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
  display: none !important;
}

.sidebar-kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 8px 0; }
.sidebar-kpi {
  background: rgba(15, 23, 42, 0.38);
  border: 1px solid rgba(34, 211, 238, 0.26);
  border-radius: 12px;
  padding: 10px 11px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 4px 12px rgba(15, 23, 42, 0.18);
}
.sidebar-kpi.wide { grid-column: 1 / -1; }
.sidebar-kpi .lbl {
  font-size: 9px; font-weight: 800; color: #A5F3FC !important;
  text-transform: uppercase; letter-spacing: 0.07em;
}
.sidebar-kpi .val {
  margin-top: 5px; font-size: 20px; font-weight: 800; color: #FFFFFF !important;
  letter-spacing: -0.02em; line-height: 1.15; word-break: break-word;
}
.sidebar-kpi .val.sm { font-size: 12px; font-weight: 700; color: #E0F2FE !important; }

.sidebar-mode {
  font-size: 12px; color: #E2E8F0 !important; font-weight: 500;
  padding: 8px 10px; margin-bottom: 6px; border-radius: 10px;
  background: rgba(15, 23, 42, 0.22);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

section[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, rgba(29, 78, 216, 0.75), rgba(14, 165, 233, 0.45)) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(34, 211, 238, 0.45) !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
  min-height: 42px !important;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.25) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  border-color: #22D3EE !important;
  filter: brightness(1.08);
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.35), 0 8px 18px rgba(15, 23, 42, 0.3) !important;
}
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
  background: rgba(15, 23, 42, 0.35) !important;
  border: 1px solid rgba(34, 211, 238, 0.25) !important;
  border-radius: 12px !important;
}
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary,
section[data-testid="stSidebar"] div[data-testid="stExpander"] p,
section[data-testid="stSidebar"] div[data-testid="stExpander"] span {
  color: #E2E8F0 !important;
}
section[data-testid="stSidebar"] .stSuccess {
  background: rgba(22, 163, 74, 0.18) !important;
  color: #BBF7D0 !important;
  border: 1px solid rgba(74, 222, 128, 0.35) !important;
}

/* ===== Form controls — high contrast, readable ===== */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  border-radius: 12px !important;
  border: 1px solid #CBD5E1 !important;
  background: #FFFFFF !important;
  color: #0F172A !important;
  -webkit-text-fill-color: #0F172A !important;
  caret-color: #0F172A !important;
  min-height: 44px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
  color: #64748B !important;
  -webkit-text-fill-color: #64748B !important;
  opacity: 1 !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: #1D4ED8 !important;
  box-shadow: 0 0 0 3px rgba(29,78,216,0.18) !important;
}
.stTextArea textarea { min-height: 120px !important; }

/* ===== Dropdowns — same navy→blue gradient as .app-header ===== */
.stSelectbox div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  border-radius: 16px !important;
  min-height: 48px !important;
  padding-left: 14px !important;
  padding-right: 12px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  box-shadow:
    0 8px 24px rgba(15, 23, 42, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
  transition: all 0.2s ease !important;
}
.stSelectbox div[data-baseweb="select"] > div:hover,
div[data-baseweb="select"] > div:hover {
  border-color: rgba(34, 211, 238, 0.55) !important;
  box-shadow:
    0 10px 28px rgba(29, 78, 216, 0.28),
    0 0 0 1px rgba(34, 211, 238, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.16) !important;
  filter: brightness(1.06);
}
.stSelectbox div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {
  border-color: rgba(34, 211, 238, 0.65) !important;
  box-shadow:
    0 0 0 3px rgba(34, 211, 238, 0.22),
    0 10px 28px rgba(29, 78, 216, 0.25) !important;
}
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div,
div[data-baseweb="select"] span,
div[data-baseweb="select"] div,
[data-testid="stSelectbox"] span {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
}
.stSelectbox [data-baseweb="select"] div[aria-disabled="true"] span,
div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p {
  color: #CBD5E1 !important;
  -webkit-text-fill-color: #CBD5E1 !important;
}
.stSelectbox svg,
div[data-baseweb="select"] svg,
[data-baseweb="select"] [data-testid="stSelectboxChevron"] svg,
div[data-baseweb="select"] > div > div:last-child svg {
  fill: #E0F2FE !important;
  color: #E0F2FE !important;
  transition: all 0.2s ease !important;
}
.stSelectbox div[data-baseweb="select"]:hover svg,
div[data-baseweb="select"]:hover svg {
  fill: #22D3EE !important;
  color: #22D3EE !important;
}

div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] [data-baseweb="menu"],
ul[role="listbox"],
ul[data-baseweb="menu"],
div[data-baseweb="menu"],
div[role="listbox"] {
  background: linear-gradient(160deg, #0F172A 0%, #1E3A8A 50%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(255, 255, 255, 0.16) !important;
  border-radius: 16px !important;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.32) !important;
  transition: all 0.2s ease !important;
  animation: ceDropdownIn 180ms ease-out !important;
  overflow: hidden !important;
}
@keyframes ceDropdownIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

ul[role="listbox"] li,
ul[data-baseweb="menu"] li,
div[data-baseweb="menu"] li,
div[role="option"],
li[role="option"],
[data-baseweb="menu"] [role="option"] {
  background: transparent !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  border-left: 4px solid transparent !important;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22) !important;
  padding-top: 12px !important;
  padding-bottom: 12px !important;
  padding-left: 14px !important;
  transition: all 0.2s ease !important;
}
ul[role="listbox"] li:last-child,
ul[data-baseweb="menu"] li:last-child,
div[role="option"]:last-child {
  border-bottom: none !important;
}
ul[role="listbox"] li span,
ul[data-baseweb="menu"] li span,
div[role="option"] span,
li[role="option"] * {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
}

ul[role="listbox"] li:hover,
ul[data-baseweb="menu"] li:hover,
div[role="option"]:hover,
li[role="option"]:hover,
[data-baseweb="menu"] [role="option"]:hover {
  background: rgba(37, 99, 235, 0.55) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  border-left-color: #22D3EE !important;
}
ul[role="listbox"] li:hover *,
ul[data-baseweb="menu"] li:hover *,
div[role="option"]:hover * {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
}

ul[role="listbox"] li[aria-selected="true"],
ul[data-baseweb="menu"] li[aria-selected="true"],
div[role="option"][aria-selected="true"],
li[aria-selected="true"],
li[aria-selected="true"]:hover,
[data-baseweb="menu"] [role="option"][aria-selected="true"] {
  background: linear-gradient(90deg, rgba(29, 78, 216, 0.95), rgba(14, 165, 233, 0.45)) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 600 !important;
  border-left: 4px solid #22D3EE !important;
}
ul[role="listbox"] li[aria-selected="true"] *,
div[role="option"][aria-selected="true"] * {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 600 !important;
}

ul[role="listbox"] li[aria-disabled="true"],
ul[data-baseweb="menu"] li[aria-disabled="true"],
div[role="option"][aria-disabled="true"],
li[aria-disabled="true"] {
  background: rgba(51, 65, 85, 0.55) !important;
  color: #94A3B8 !important;
  -webkit-text-fill-color: #94A3B8 !important;
  pointer-events: none !important;
}

[data-baseweb="menu"] hr,
[data-baseweb="menu"] li[role="separator"],
ul[role="listbox"] hr {
  border-color: rgba(148, 163, 184, 0.28) !important;
  background: rgba(148, 163, 184, 0.28) !important;
}

ul[role="listbox"],
ul[data-baseweb="menu"],
div[data-baseweb="menu"],
div[data-baseweb="popover"] > div {
  scrollbar-width: thin !important;
  scrollbar-color: rgba(148, 163, 184, 0.55) transparent !important;
}
ul[role="listbox"]::-webkit-scrollbar,
ul[data-baseweb="menu"]::-webkit-scrollbar,
div[data-baseweb="menu"]::-webkit-scrollbar,
div[data-baseweb="popover"] > div::-webkit-scrollbar {
  width: 8px !important;
}
ul[role="listbox"]::-webkit-scrollbar-track,
ul[data-baseweb="menu"]::-webkit-scrollbar-track,
div[data-baseweb="menu"]::-webkit-scrollbar-track,
div[data-baseweb="popover"] > div::-webkit-scrollbar-track {
  background: transparent !important;
  border-radius: 16px !important;
}
ul[role="listbox"]::-webkit-scrollbar-thumb,
ul[data-baseweb="menu"]::-webkit-scrollbar-thumb,
div[data-baseweb="menu"]::-webkit-scrollbar-thumb,
div[data-baseweb="popover"] > div::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.45) !important;
  border-radius: 8px !important;
}
ul[role="listbox"]::-webkit-scrollbar-thumb:hover,
ul[data-baseweb="menu"]::-webkit-scrollbar-thumb:hover,
div[data-baseweb="menu"]::-webkit-scrollbar-thumb:hover,
div[data-baseweb="popover"] > div::-webkit-scrollbar-thumb:hover {
  background: #22D3EE !important;
}

/* Number steppers — compact +/− controls */
.stNumberInput button,
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] [data-testid="stNumberInputStepDown"],
[data-testid="stNumberInput"] [data-testid="stNumberInputStepUp"] {
  background: #F8FAFC !important;
  color: #334155 !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 6px !important;
  min-width: 28px !important;
  width: 28px !important;
  height: 28px !important;
  padding: 0 !important;
  font-size: 12px !important;
  line-height: 1 !important;
}
.stNumberInput button:hover {
  background: #EEF2FF !important;
  color: #1D4ED8 !important;
  border-color: #BFDBFE !important;
}
div[data-testid="stNumberInput"] > div {
  gap: 4px !important;
}
[data-testid="stNumberInput"] input {
  min-height: 38px !important;
  font-size: 14px !important;
}

/* Form section cards spacing */
.form-grid-gap { margin-bottom: 4px; }
.bmi-live {
  margin-top: 8px; padding: 10px 12px; border-radius: 10px;
  background: #EFF6FF; border: 1px solid #BFDBFE;
  color: #1E3A8A; font-size: 13px; font-weight: 600;
}
.summary-card {
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  border: 1px solid var(--border); border-radius: 16px;
  padding: 18px 20px; margin: 16px 0 8px 0; box-shadow: var(--shadow);
}
.summary-card h3 {
  margin: 0 0 6px 0; font-size: 16px; font-weight: 800; color: var(--navy);
}
.summary-card .cap { font-size: 12px; color: var(--muted); margin-bottom: 14px; }
.summary-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}
.summary-cell {
  background: #FFFFFF; border: 1px solid var(--border); border-radius: 12px;
  padding: 12px 14px;
}
.summary-cell .lbl { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.summary-cell .val { margin-top: 6px; font-size: 18px; font-weight: 800; color: var(--navy); }
.summary-cell .sub { margin-top: 4px; font-size: 12px; color: var(--muted); line-height: 1.4; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: 1fr; }
}

label, .stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label,
[data-testid="stWidgetLabel"] p {
  font-size: 13px !important; font-weight: 700 !important; color: #0F172A !important;
}

/* Checkbox readable */
.stCheckbox label p { color: #0F172A !important; font-weight: 600 !important; }
.stCheckbox [data-baseweb="checkbox"] {
  border-color: #64748B !important;
  background: #FFFFFF !important;
}

div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  margin-bottom: 10px; box-shadow: var(--shadow);
}

.stButton > button {
  border-radius: 12px !important; font-weight: 700 !important; font-size: 14px !important;
  min-height: 46px !important; border: 1px solid var(--border) !important;
  background: #FFFFFF !important; color: var(--navy) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #1D4ED8, #2563EB) !important;
  color: #FFFFFF !important; border: none !important;
  box-shadow: 0 8px 18px rgba(29, 78, 216, 0.28) !important;
}
.stButton > button[kind="primary"]:hover {
  filter: brightness(1.05);
}

div[data-testid="stMetricValue"] { font-size: 26px !important; color: var(--navy) !important; font-weight: 800 !important; }
div[data-testid="stMetricLabel"] { font-size: 12px !important; color: var(--muted) !important; font-weight: 600 !important; }

.stTabs [data-baseweb="tab-list"] {
  gap: 8px; background: transparent; border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  font-size: 13px; font-weight: 650; color: var(--muted);
  padding: 10px 14px; border-radius: 10px 10px 0 0;
}
.stTabs [aria-selected="true"] {
  color: var(--blue) !important; background: #EFF6FF !important;
}

div[data-testid="stRadio"] > div { gap: 8px; }
hr { border-color: var(--border) !important; }
</style>
"""

TOPIC_OPTIONS: dict[str, list[str]] = {
    "Cardiovascular / Statins": [
        "What statin intensity is recommended for adults with clinical ASCVD?",
        "When is a statin recommended for primary prevention of CVD?",
        "How is ASCVD risk estimation used in prevention discussions?",
    ],
    "Diabetes / A1C": [
        "What A1C target is commonly used for nonpregnant adults with type 2 diabetes?",
        "Who should be screened for prediabetes and type 2 diabetes?",
        "What are key themes in diabetes management from public educational sources?",
    ],
    "Hypertension / Blood pressure": [
        "When should adults be screened for hypertension according to USPSTF?",
        "What are ACC/AHA blood pressure categories?",
        "What lifestyle measures help lower blood pressure?",
    ],
    "Lifestyle / Prevention": [
        "What lifestyle counseling themes support cardiovascular prevention?",
        "How does shared decision making apply to preventive therapy choices?",
        "What lifestyle changes help high blood pressure?",
    ],
}

ALL_SAMPLES = ["— Type below instead —"] + [q for qs in TOPIC_OPTIONS.values() for q in qs]

EVIDENCE_CATEGORIES = [
    {
        "key": "guidelines",
        "title": "Clinical Practice Guidelines",
        "priority_label": "Priority 1",
        "priorities": {1},
        "featured": True,
        "accent": "#1D4ED8",
        "org_hints": ["USPSTF", "ADA", "AHA/ACC", "NCCN", "NICE", "WHO"],
    },
    {
        "key": "systematic",
        "title": "Systematic Reviews & Meta-Analyses",
        "priority_label": "Priority 2",
        "priorities": {2},
        "featured": False,
        "accent": "#0F766E",
        "org_hints": ["Cochrane", "JAMA", "BMJ"],
    },
    {
        "key": "rcts",
        "title": "Randomized Controlled Trials",
        "priority_label": "Priority 3",
        "priorities": {3},
        "featured": False,
        "accent": "#B45309",
        "org_hints": ["NEJM", "Lancet", "RCT"],
    },
    {
        "key": "pubmed",
        "title": "PubMed / PubMed Central",
        "priority_label": "Priority 4",
        "priorities": {4},
        "featured": False,
        "accent": "#6D28D9",
        "org_hints": ["PubMed", "PMC", "NLM"],
    },
    {
        "key": "government",
        "title": "Government Medical Resources",
        "priority_label": "Priority 5–6",
        "priorities": {5, 6},
        "featured": False,
        "accent": "#C2410C",
        "org_hints": ["AHRQ", "CDC", "MedlinePlus", "NIH", "FDA"],
    },
    {
        "key": "other",
        "title": "Other Supporting Evidence",
        "priority_label": "Priority 7+",
        "priorities": {7},
        "featured": False,
        "accent": "#475569",
        "org_hints": ["MedQuAD", "Educational sample"],
    },
]


def inject_theme() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)


def _esc(s: object) -> str:
    return html.escape("" if s is None else str(s))


def _short_org(name: str) -> str:
    n = (name or "").strip()
    mapping = [
        ("uspstf", "USPSTF"),
        ("american diabetes", "ADA"),
        ("ada", "ADA"),
        ("acc/aha", "AHA/ACC"),
        ("acc", "ACC"),
        ("aha", "AHA"),
        ("cochrane", "Cochrane"),
        ("medlineplus", "MedlinePlus"),
        ("ahrq", "AHRQ"),
        ("pubmed", "PubMed"),
        ("pmc", "PMC"),
        ("cdc", "CDC"),
        ("nice", "NICE"),
        ("who", "WHO"),
        ("nccn", "NCCN"),
        ("medquad", "MedQuAD"),
        ("nejm", "NEJM"),
        ("lancet", "Lancet"),
        ("jama", "JAMA"),
    ]
    low = n.lower()
    for key, label in mapping:
        if key in low:
            return label
    return n.split("(")[0].split("—")[0].strip()[:28] or "Source"


def _year_val(h: dict) -> int:
    for k in ("published_year", "year"):
        v = h.get(k)
        try:
            return int(str(v)[:4])
        except (TypeError, ValueError):
            continue
    return 0


def sort_hits_for_display(docs: list[dict]) -> list[dict]:
    return sorted(
        docs,
        key=lambda h: (
            -_year_val(h),
            -float(h.get("score") or 0.0),
            -float(h.get("semantic_score") or 0.0),
            int(h.get("evidence_tier") or 99),
        ),
    )


def evidence_mode_labels(result: dict | None = None) -> dict[str, bool]:
    ku = (result or {}).get("knowledge_update") or {}
    live_probe = bool(ku) and not ku.get("skipped", True)
    return {
        "indexed": True,
        "cached": True,
        "offline": not llm_configured(),
        "live": live_probe,
    }


def provenance_badge_html(modes: dict[str, bool]) -> str:
    bits = ['<span class="badge badge-indexed">Indexed evidence</span>']
    if modes.get("cached"):
        bits.append('<span class="badge badge-cached">Cached index</span>')
    if modes.get("offline"):
        bits.append('<span class="badge badge-offline">Offline fallback</span>')
    if modes.get("live"):
        bits.append('<span class="badge badge-live">Live source check</span>')
    else:
        bits.append('<span class="badge badge-cached">Not live API retrieval</span>')
    return " ".join(bits)


def group_hits_by_category(hits: list) -> dict:
    grouped = {c["key"]: [] for c in EVIDENCE_CATEGORIES}
    for h in hits or []:
        try:
            p = int(h.get("evidence_tier") or 99)
        except (TypeError, ValueError):
            p = 99
        placed = False
        for c in EVIDENCE_CATEGORIES:
            if p in c["priorities"]:
                grouped[c["key"]].append(h)
                placed = True
                break
        if not placed:
            grouped["other"].append(h)
    for k in grouped:
        grouped[k] = sort_hits_for_display(grouped[k])
    return grouped


def render_header() -> None:
    st.markdown(
        """
        <div class="app-header">
          <div class="app-header-inner">
            <div class="brand-mark">CE</div>
            <div>
              <h1>Clinical Evidence CDSS</h1>
              <div class="subtitle">
                Enterprise clinical decision-support workspace for source-linked recommendations,
                evidence hierarchy, and transparent clinician review. Supports judgment — does not replace it.
              </div>
              <div class="pills">
                <span class="pill">Guidelines-first retrieval</span>
                <span class="pill">7-step CDSS workflow</span>
                <span class="pill">University research prototype</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="app-footer">
          <strong>Developed by Audrey Rah</strong><br/>
          University of Houston · Houston, Texas, USA<br/>
          Research Prototype — Clinical Decision Support System<br/>
          {_esc(APP_DISCLAIMER)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_evidence_category_tiles(hits: list, result: dict | None = None) -> None:
    modes = evidence_mode_labels(result)
    st.markdown(
        f'<div class="card-caption">{provenance_badge_html(modes)}'
        f"&nbsp;&nbsp;Sources come from the indexed knowledge base unless a live source check was enabled.</div>",
        unsafe_allow_html=True,
    )
    grouped = group_hits_by_category(hits)

    cards = ['<div class="ev-grid">']
    for cat in EVIDENCE_CATEGORIES:
        docs = grouped[cat["key"]]
        orgs: list[str] = []
        for h in docs:
            label = _short_org(str(h.get("organization") or ""))
            if label and label not in orgs:
                orgs.append(label)
        n_docs = len({h.get("doc_id") for h in docs})
        featured = " featured" if cat.get("featured") else ""
        accent = cat.get("accent", "#1D4ED8")
        if n_docs == 0:
            body = '<div class="empty">No documents for this query.</div>'
        else:
            org_lines = "".join(f'<div class="org">{_esc(o)}</div>' for o in orgs[:6])
            top = docs[0]
            body = (
                f"{org_lines}"
                f'<div class="meta">{n_docs} source{"s" if n_docs != 1 else ""} · {_esc(cat["priority_label"])}</div>'
                f'<div class="org" style="margin-top:8px;color:#64748B;">Lead: {_esc((top.get("title") or "")[:68])}</div>'
            )
        cards.append(
            f'<div class="ev-tile{featured}" style="--accent:{accent}; border-top-color:{accent};">'
            f'<h4>{_esc(cat["title"])}</h4>{body}</div>'
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)

    st.markdown('<div class="card-title sm" style="margin-top:16px;">Source details</div>', unsafe_allow_html=True)

    for cat in EVIDENCE_CATEGORIES:
        docs = grouped[cat["key"]]
        n_docs = len({h.get("doc_id") for h in docs})
        orgs = []
        for h in docs:
            label = _short_org(str(h.get("organization") or ""))
            if label and label not in orgs:
                orgs.append(label)
        header = f"{cat['title']}  ·  {n_docs}  ·  {cat['priority_label']}"
        if orgs:
            header += f"  ·  {', '.join(orgs[:4])}"
        with st.expander(header, expanded=(bool(cat.get("featured")) and n_docs > 0)):
            if not docs:
                st.info(f"No {cat['title']} retrieved for this question.")
                continue
            for i, h in enumerate(docs, 1):
                year = h.get("published_year") or h.get("year") or "—"
                score = float(h.get("score") or 0.0)
                sem = float(h.get("semantic_score") or 0.0)
                url = h.get("url") or "#"
                alt = " alt" if i % 2 == 0 else ""
                conf_pct = min(99, max(1, int(round(score * 100))))
                st.markdown(
                    f"""
                    <div class="source-card{alt}">
                      <div class="title">{i}. {_esc(h.get('title'))}</div>
                      <div class="meta">
                        <strong>Category:</strong> {_esc(cat['title'])}<br/>
                        <strong>Organization:</strong> {_esc(h.get('organization'))}<br/>
                        <strong>Publication / update year:</strong> {_esc(year)}<br/>
                        <strong>Evidence level:</strong> {_esc(h.get('evidence_level'))} ·
                        <strong>Priority:</strong> P{_esc(h.get('evidence_tier'))}<br/>
                        <strong>Relevance score:</strong> {score:.3f} ·
                        <strong>Semantic score:</strong> {sem:.3f} ·
                        <strong>Confidence (rank):</strong> {conf_pct}%<br/>
                        <strong>Status:</strong> {_esc(h.get('status', 'active'))}
                        {" · SUPERSEDED" if h.get("superseded") else ""}
                      </div>
                      <div style="margin-top:10px;">
                        <a href="{_esc(url)}" target="_blank" rel="noopener noreferrer">Open original source</a>
                        &nbsp;&nbsp;<span class="badge badge-indexed">Indexed evidence</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.popover(f"Excerpt {i}"):
                    st.write(h.get("text"))
                    if h.get("rank_breakdown"):
                        st.json(h.get("rank_breakdown"))


@st.cache_resource(show_spinner=False)
def load_store():
    from src.vectorstore import VectorStore

    store = VectorStore()
    store.load()
    return store


@st.cache_resource(show_spinner=False)
def load_graph():
    from src.graph import get_app

    return get_app()


def run_question(
    question: str,
    patient_input: dict | None = None,
    run_knowledge_update: bool = False,
) -> dict:
    from src import vectorstore as vs_mod
    from src.graph import run_pipeline

    vs_mod._STORE = load_store()
    load_graph()
    return run_pipeline(
        question,
        patient_input=patient_input or {},
        run_knowledge_update=run_knowledge_update,
    )


def _parse_optional_float(raw: str | None) -> float | None:
    s = (raw or "").strip().lower()
    if not s or s in {"unknown", "n/a", "na", "-", "none"}:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _parse_optional_int(raw: str | None) -> int | None:
    v = _parse_optional_float(raw)
    if v is None:
        return None
    return int(round(v))


def _calc_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    meters = height_cm / 100.0
    return round(weight_kg / (meters * meters), 1)


DIABETES_UI_TO_CODE = {
    "Unknown": None,
    "No Diabetes": "none",
    "Prediabetes": "prediabetes",
    "Type 1 Diabetes": "type1",
    "Type 2 Diabetes": "type2",
}

SEX_UI_TO_CODE = {
    "Unknown": None,
    "Female": "female",
    "Male": "male",
    "Other": "other",
}

# Meaningful BP categories → representative systolic values for existing pipeline fields
SBP_UI_TO_VALUE = {
    "Unknown": None,
    "Normal (<120 mm Hg)": 110,
    "Elevated (120–129 mm Hg)": 125,
    "High — Stage 1 (130–139 mm Hg)": 135,
    "High — Stage 2 (140–179 mm Hg)": 150,
    "Critical / Hypertensive crisis (>=180 mm Hg)": 190,
}

# Meaningful LDL categories → representative values for existing pipeline fields
LDL_UI_TO_VALUE = {
    "Unknown": None,
    "Optimal (<100 mg/dL)": 90,
    "Near optimal (100–129 mg/dL)": 115,
    "Borderline high (130–159 mg/dL)": 145,
    "High (160–189 mg/dL)": 175,
    "Critical / Very high (>=190 mg/dL)": 200,
}


def _patient_form() -> dict:
    """UI-only patient intake. Returns the same patient_input keys the pipeline expects."""
    # ----- Patient Information -----
    st.markdown(
        '<div class="card"><div class="card-title">Patient Information</div>'
        '<div class="card-caption">Demographics used for context. Leave blank or Unknown when unavailable.</div>',
        unsafe_allow_html=True,
    )
    p1, p2, p3 = st.columns(3, gap="medium")
    with p1:
        age_raw = st.text_input(
            "Age (years)",
            value="",
            placeholder="Leave blank if unavailable",
            help="Patient age in years. Used for prevention age windows and risk context.",
        )
    with p2:
        sex_label = st.selectbox(
            "Sex",
            list(SEX_UI_TO_CODE.keys()),
            help="Select the patient sex category used for clinical context.",
        )
    with p3:
        diabetes_label = st.selectbox(
            "Diabetes status",
            list(DIABETES_UI_TO_CODE.keys()),
            help="Select the clearest diabetes category: none, prediabetes, type 1, or type 2.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ----- Vital Signs -----
    st.markdown(
        '<div class="card"><div class="card-title">Vital Signs</div>'
        '<div class="card-caption">Enter measured values when known. BMI is calculated from height and weight.</div>',
        unsafe_allow_html=True,
    )
    v1, v2, v3, v4 = st.columns(4, gap="medium")
    with v1:
        sbp_label = st.selectbox(
            "Systolic blood pressure (top number)",
            list(SBP_UI_TO_VALUE.keys()),
            help="ⓘ SBP is the top number in a blood pressure reading. Choose Normal, Elevated, High, or Critical.",
        )
    with v2:
        dbp_raw = st.text_input(
            "DBP (mm Hg)",
            value="",
            placeholder="Unknown",
            help="ⓘ Diastolic blood pressure — bottom number in a BP reading (mm Hg).",
        )
    with v3:
        height_raw = st.text_input(
            "Height (cm)",
            value="",
            placeholder="e.g., 170",
            help="ⓘ Height in centimeters. Used with weight to calculate BMI automatically.",
        )
    with v4:
        weight_raw = st.text_input(
            "Weight (kg)",
            value="",
            placeholder="e.g., 75",
            help="ⓘ Weight in kilograms. Used with height to calculate BMI automatically.",
        )

    height_cm = _parse_optional_float(height_raw)
    weight_kg = _parse_optional_float(weight_raw)
    bmi = _calc_bmi(height_cm, weight_kg)
    if bmi is not None:
        st.markdown(
            f'<div class="bmi-live">Calculated BMI: <strong>{bmi}</strong> '
            f'<span style="font-weight:500;color:#64748B;">(from height {height_cm:g} cm · weight {weight_kg:g} kg)</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("BMI will appear here once both height and weight are entered.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ----- Risk Factors -----
    st.markdown(
        '<div class="card"><div class="card-title">Risk Factors</div>'
        '<div class="card-caption">Lipids, tobacco, ASCVD history, and other cardiovascular risk context.</div>',
        unsafe_allow_html=True,
    )
    r1, r2 = st.columns(2, gap="medium")
    with r1:
        ldl_label = st.selectbox(
            "LDL cholesterol level",
            list(LDL_UI_TO_VALUE.keys()),
            help="ⓘ LDL is “bad” cholesterol. Choose Optimal, Borderline high, High, or Critical / Very high.",
        )
        smoking = st.selectbox(
            "Smoking",
            ["Unknown", "never", "former", "current"],
            help="Tobacco use status for cardiovascular risk context.",
        )
    with r2:
        ascvd = st.checkbox(
            "Clinical ASCVD history (MI, stroke, revascularization, etc.)",
            help="ⓘ Atherosclerotic cardiovascular disease history — prior MI, stroke, CABG/PCI, PAD, etc.",
        )
        other = st.text_input(
            "Other CV risk factors (comma-separated)",
            placeholder="e.g., CKD, family history",
            help="Additional cardiovascular risk factors not captured above.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    return {
        "age": _parse_optional_int(age_raw),
        "sex": SEX_UI_TO_CODE.get(sex_label),
        "sbp": SBP_UI_TO_VALUE.get(sbp_label),
        "dbp": _parse_optional_int(dbp_raw),
        "diabetes": DIABETES_UI_TO_CODE.get(diabetes_label),
        "ldl": LDL_UI_TO_VALUE.get(ldl_label),
        "bmi": bmi,
        "smoking": None if smoking == "Unknown" else smoking,
        "clinical_ascvd": True if ascvd else None,
        "other_cv_risk_factors": [x.strip() for x in other.split(",") if x.strip()],
    }


def _render_prediction_summary(result: dict) -> None:
    """UI-only summary card from existing pipeline outputs (no new ML)."""
    risk = result.get("risk_analysis") or {}
    conf = float(result.get("confidence") or 0.0)
    band = (risk.get("cv_risk_band_prototype") or "unknown").replace("_", " ")
    factors = risk.get("cardiovascular_risk_factors") or []
    top = ", ".join(str(f).replace("_", " ") for f in factors[:5]) if factors else "Insufficient structured factors"
    more = f" · +{len(factors) - 5} more" if len(factors) > 5 else ""
    st.markdown(
        f"""
        <div class="summary-card">
          <h3>Prediction summary</h3>
          <div class="cap">Derived from the existing CDSS risk analysis and verification confidence — not a validated clinical calculator.</div>
          <div class="summary-grid">
            <div class="summary-cell">
              <div class="lbl">Estimated risk</div>
              <div class="val">{_esc(band.title())}</div>
              <div class="sub">Prototype CV risk band</div>
            </div>
            <div class="summary-cell">
              <div class="lbl">Confidence</div>
              <div class="val">{conf*100:.0f}%</div>
              <div class="sub">Evidence verification confidence</div>
            </div>
            <div class="summary-cell">
              <div class="lbl">Key contributing factors</div>
              <div class="val" style="font-size:14px;line-height:1.45;">{_esc(top)}{_esc(more)}</div>
              <div class="sub">From structured risk analysis</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_theme()
    render_header()
    st.markdown(f'<div class="disclaimer">{_esc(APP_DISCLAIMER)}</div>', unsafe_allow_html=True)

    with st.sidebar:
        try:
            meta = load_store().meta or {}
            n_docs = meta.get("n_docs", "—")
            n_chunks = meta.get("n_chunks", "—")
            embedder = meta.get("embedder", "—")
            index_ok = True
            index_err = ""
        except Exception as exc:
            n_docs, n_chunks, embedder = "—", "—", "—"
            index_ok = False
            index_err = str(exc)

        llm_label = "Configured" if llm_configured() else "Offline Fallback"

        st.markdown(
            """
            <div class="sidebar-shell">
              <div class="sidebar-brand">
                <div class="mark">CE</div>
                <div>
                  <div class="name">Clinical Evidence</div>
                  <div class="role">Decision Support Workspace</div>
                </div>
              </div>
              <div class="sidebar-section">Navigation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        nav = st.radio(
            "Workspace navigation",
            ["Clinical workspace", "About"],
            label_visibility="collapsed",
        )

        st.markdown(
            f"""
            <div class="sidebar-shell">
              <div class="sidebar-section">System status</div>
              <div class="sidebar-kpi-grid">
                <div class="sidebar-kpi"><div class="lbl">Indexed documents</div><div class="val">{_esc(n_docs)}</div></div>
                <div class="sidebar-kpi"><div class="lbl">Chunks</div><div class="val">{_esc(n_chunks)}</div></div>
                <div class="sidebar-kpi wide"><div class="lbl">Embedding</div><div class="val sm">{_esc(embedder)}</div></div>
                <div class="sidebar-kpi wide"><div class="lbl">LLM</div><div class="val sm">{_esc(llm_label)}</div></div>
                <div class="sidebar-kpi wide"><div class="lbl">Top-k</div><div class="val">{_esc(TOP_K)}</div></div>
              </div>

              <div class="sidebar-section">Evidence modes</div>
              <div class="sidebar-mode">Indexed · local FAISS knowledge base</div>
              <div class="sidebar-mode">Cached · session / local index</div>
              <div class="sidebar-mode">Offline fallback · no LLM key</div>
              <div class="sidebar-mode">Live source check · URL probe when enabled</div>

              <div class="sidebar-section">Maintenance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not index_ok:
            st.error(f"Index not ready: {index_err}")

        if st.button("Knowledge update", use_container_width=True):
            from src import vectorstore as vs_mod
            from src.knowledge_update import run_knowledge_update

            with st.spinner("Checking authoritative source URLs..."):
                report = run_knowledge_update(rebuild_index=True)
            load_store.clear()
            vs_mod._STORE = None
            load_store()
            st.session_state["update_report"] = report
            st.success(f"Checked {report.get('n_sources')} sources.")
        if st.session_state.get("update_report"):
            with st.expander("Last update report"):
                st.json(st.session_state["update_report"])
        if st.button("Rebuild index", use_container_width=True):
            from src import vectorstore as vs_mod
            from src.vectorstore import VectorStore

            load_store.clear()
            vs_mod._STORE = None
            VectorStore().build_from_seed(force=True)
            load_store()
            st.success("Index rebuilt")
            st.rerun()

    if nav == "About":
        st.markdown(
            """
            <div class="card">
              <div class="card-title">About</div>
              <div class="card-caption">Visual product surface only — backend workflow unchanged.</div>
              <p style="font-size:15px;line-height:1.6;color:#0F172A;margin:0;">
                Clinical Evidence CDSS is a university research prototype for source-linked decision support.
                It presents patient context, priority-ranked evidence, verification notes, and structured
                recommendations with citations for clinician review.
              </p>
              <p style="font-size:13px;color:#64748B;margin-top:16px;line-height:1.7;">
                <strong style="color:#0F172A;">Developed by Audrey Rah</strong><br/>
                University of Houston<br/>
                Houston, Texas, USA
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_footer()
        return

    patient_input = _patient_form()

    st.markdown(
        '<div class="card"><div class="card-title">Clinical query</div>'
        '<div class="card-caption">Compose a clinician-style question or note. Templates are optional.</div>',
        unsafe_allow_html=True,
    )
    topic = st.selectbox("Template topic", ["All topics"] + list(TOPIC_OPTIONS.keys()))
    choices = ALL_SAMPLES if topic == "All topics" else ["— Type below instead —"] + TOPIC_OPTIONS[topic]
    picked = st.selectbox("Ready questions", choices)

    if "question_text" not in st.session_state:
        st.session_state["question_text"] = (
            "55-year-old male with BP 138/88, BMI 31, type 2 diabetes, LDL 145, current smoker — "
            "what preventive and lipid strategies should be considered?"
        )

    if picked != "— Type below instead —":
        if st.session_state.get("_last_picked") != picked:
            st.session_state["question_text"] = picked
            st.session_state["_last_picked"] = picked
    else:
        st.session_state["_last_picked"] = picked

    st.text_area(
        "Clinical question / note",
        key="question_text",
        height=128,
        placeholder="Example: 55-year-old male, BP 138/88, BMI 31, T2DM, LDL 145, current smoker — preventive lipid strategy?",
    )

    c1, c2 = st.columns([3, 1], gap="medium")
    with c1:
        ask = st.button("Run CDSS workflow", type="primary", use_container_width=True)
    with c2:
        also_update = st.checkbox(
            "Live source check",
            value=False,
            help="Runs Knowledge Update URL probes for this run only. Does not mean full live guideline ingestion.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if ask:
        q = (st.session_state.get("question_text") or "").strip()
        if not q:
            st.error("Please enter a clinical question or note.")
        else:
            with st.spinner("Running CDSS workflow…"):
                try:
                    result = run_question(q, patient_input=patient_input, run_knowledge_update=also_update)
                    st.session_state["last_result"] = result
                    st.session_state["last_question"] = q
                except Exception as exc:
                    st.error(f"Run failed: {exc}")

    result = st.session_state.get("last_result")
    if not result:
        st.info("Complete assessment fields as available, enter a clinical query, then run the workflow.")
        render_footer()
        return

    timings = result.get("timings") or {}
    hits = result.get("hits") or []
    n_chunks = int(timings.get("n_chunks", len(hits)))
    n_guidelines = sum(1 for h in hits if int(h.get("evidence_tier") or 99) == 1)
    conf = float(result.get("confidence") or 0.0)
    total_s = float(timings.get("total_pipeline_s") or 0.0)

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi"><div class="label">Confidence</div><div class="value">{conf*100:.0f}%</div><div class="hint">Verification confidence</div></div>
          <div class="kpi"><div class="label">Evidence retrieved</div><div class="value">{n_chunks}</div><div class="hint">Ranked source chunks</div></div>
          <div class="kpi"><div class="label">Guidelines</div><div class="value">{n_guidelines}</div><div class="hint">Priority 1 sources</div></div>
          <div class="kpi"><div class="label">Response time</div><div class="value">{total_s:.2f}s</div><div class="hint">End-to-end pipeline</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Query: {st.session_state.get('last_question', '')}")
    if result.get("needs_human_review"):
        st.warning("Human review recommended — incomplete data, limited evidence, or source disagreement.")

    modes = evidence_mode_labels(result)
    st.markdown(provenance_badge_html(modes), unsafe_allow_html=True)

    _render_prediction_summary(result)

    tabs = st.tabs(
        [
            "1 Assessment",
            "2 Risk analysis",
            "3 Retrieved evidence",
            "4 Verification",
            "5 Recommendations",
            "6 Evidence summary",
            "7 Transparency",
            "Full narrative",
        ]
    )

    patient = result.get("patient_assessment") or {}
    risk = result.get("risk_analysis") or {}
    ver = result.get("verification") or {}
    rec = result.get("recommendation") or {}

    with tabs[0]:
        st.markdown('<div class="card"><div class="card-title">Patient assessment</div>', unsafe_allow_html=True)
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Age", patient.get("age") if patient.get("age") is not None else "—")
        a2.metric("Sex", patient.get("sex") or "—")
        a3.metric("BP", f"{patient.get('sbp') or '—'}/{patient.get('dbp') or '—'}")
        a4.metric("BMI", patient.get("bmi") if patient.get("bmi") is not None else "—")
        b1, b2, b3, b4 = st.columns(4)
        b1.write(f"**Diabetes:** {patient.get('diabetes') or '—'}")
        b2.write(f"**LDL:** {patient.get('ldl') if patient.get('ldl') is not None else '—'}")
        b3.write(f"**Smoking:** {patient.get('smoking') or '—'}")
        b4.write(f"**Clinical ASCVD:** {patient.get('clinical_ascvd')}")
        st.write("**Other CV risk factors:**", ", ".join(patient.get("other_cv_risk_factors") or []) or "—")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="card"><div class="card-title">Clinical risk analysis</div>', unsafe_allow_html=True)
        st.write("**Cardiovascular risk factors:**", ", ".join(risk.get("cardiovascular_risk_factors") or []) or "—")
        st.write("**Obesity status:**", risk.get("obesity_status"))
        st.write("**Hypertension stage:**", risk.get("hypertension_stage"))
        st.write("**Diabetes-related risk:**", risk.get("diabetes_related_risk"))
        st.write("**Preventive care needs:**")
        for n in risk.get("preventive_care_needs") or []:
            st.markdown(f"- {n.replace('_', ' ')}")
        st.write("**Prototype CV risk band:**", risk.get("cv_risk_band_prototype"))
        for note in risk.get("analysis_notes") or []:
            st.caption(note)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown(
            '<div class="card"><div class="card-title">Retrieved evidence</div>'
            '<div class="card-caption">Guidelines are emphasized first. Expand a category for citations and links.</div>',
            unsafe_allow_html=True,
        )
        st.caption(result.get("ranking_policy") or "")
        render_evidence_category_tiles(hits, result=result)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div class="card"><div class="card-title">Evidence verification</div>', unsafe_allow_html=True)
        st.write("**Organizations consulted:**", ", ".join(ver.get("organizations_consulted") or []) or "—")
        st.markdown("**Agreements**")
        for a in ver.get("agreements") or []:
            st.success(a)
        st.markdown("**Conflicts / disagreements**")
        conflicts = ver.get("conflicts") or []
        if not conflicts:
            st.info("No strong cross-source conflicts flagged.")
        for c in conflicts:
            st.error(c.get("message"))
            st.json(c.get("sources_involved"))
        if ver.get("notes"):
            st.caption("Notes: " + "; ".join(ver["notes"]))
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[4]:
        st.markdown('<div class="card"><div class="card-title">Clinical recommendations</div>', unsafe_allow_html=True)
        for title, key in [
            ("Lifestyle", "lifestyle_recommendations"),
            ("Medication", "medication_recommendations"),
            ("Screening", "screening_recommendations"),
            ("Follow-up", "follow_up_recommendations"),
            ("Preventive strategies", "preventive_strategies"),
        ]:
            st.markdown(f'<div class="card-title sm">{title}</div>', unsafe_allow_html=True)
            for item in rec.get(key) or []:
                st.markdown(
                    f"""
                    <div class="rec-item">
                      <div class="body">{_esc(item.get('recommendation'))}</div>
                      <div class="meta">{_esc(item.get('organization'))} · {_esc(item.get('publication_year'))} ·
                      {_esc(item.get('evidence_level'))} · cites {_esc(item.get('supporting_citations'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[5]:
        st.markdown('<div class="card"><div class="card-title">Evidence summary</div>', unsafe_allow_html=True)
        for i, row in enumerate(rec.get("evidence_summary") or [], 1):
            alt = " alt" if i % 2 == 0 else ""
            st.markdown(
                f"""
                <div class="source-card{alt}">
                  <div class="title">{_esc(row.get('category'))}</div>
                  <div class="meta">
                    {_esc(row.get('recommendation'))}<br/><br/>
                    Guideline: {_esc(row.get('guideline_name'))}<br/>
                    Organization: {_esc(row.get('organization'))} · Year: {_esc(row.get('publication_year'))}<br/>
                    Evidence level: {_esc(row.get('evidence_level'))}<br/>
                    Citation: {_esc(row.get('citation'))}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('<div class="card-title sm">Citation list</div>', unsafe_allow_html=True)
        for c in rec.get("citations") or []:
            st.markdown(c.get("citation"))
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[6]:
        st.markdown('<div class="card"><div class="card-title">Transparency</div>', unsafe_allow_html=True)
        tr = result.get("transparency") or {}
        st.metric("Confidence", f"{tr.get('confidence', result.get('confidence', 0)):.2f}")
        st.write("**Human review recommended:**", tr.get("needs_human_review", result.get("needs_human_review")))
        st.write("**Evidence hierarchy:**", tr.get("evidence_hierarchy") or result.get("ranking_policy"))
        st.markdown(provenance_badge_html(modes), unsafe_allow_html=True)
        st.markdown("**Sources consulted**")
        for s in tr.get("sources_consulted") or []:
            st.markdown(
                f"- [{s.get('n')}] P{s.get('priority')} {s.get('organization')} — {s.get('title')} ({s.get('year')})"
            )
        st.markdown("**Agent trace**")
        for step in result.get("agent_trace") or []:
            st.markdown(f"- **{step.get('agent')}:** {step.get('detail')}")
        st.caption(tr.get("disclaimer") or APP_DISCLAIMER)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[7]:
        st.markdown('<div class="card"><div class="card-title">Full narrative</div>', unsafe_allow_html=True)
        st.markdown(result.get("final_answer") or "")
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer()


if __name__ == "__main__":
    main()
