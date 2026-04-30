"""
app.py — CryptoChain Analyzer Dashboard
Entry point. Run with: streamlit run app.py
"""

import time
import streamlit as st

from api.blockchain_client import get_blocks, get_latest_block
from modules import m1_pow, m2_header, m3_difficulty, m4_ai, m5_merkle, m6_security

st.set_page_config(
    page_title="CryptoChain Analyzer",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":     "https://mempool.space/docs/api",
        "Report a bug": "https://github.com/aledeniiz/blockchain-dashboard-aledeniiz/issues",
        "About":        "CryptoChain Analyzer — Live Bitcoin cryptographic metrics. UAX 2025-26.",
    },
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
:root {
    --bg-0:    #f6f7fb;   /* page bg — subtle off-white */
    --bg-1:    #ffffff;   /* sidebar / cards */
    --bg-2:    #ffffff;   /* surface 2 */
    --bg-3:    #f0f1f6;   /* nested blocks */
    --border:  #e3e4ec;
    --border-2:#cccfdc;
    --text:    #1a1a2e;   /* primary dark */
    --muted:   #5a5a78;   /* secondary */
    --muted-2: #8a8a9c;   /* tertiary */
    --btc:     #F7931A;
    --btc-2:   #d97a05;   /* darker for contrast on white */
    --green:   #16a34a;
    --red:     #dc2626;
    --blue:    #2563eb;
    --purple:  #7c3aed;
}

/* Global font */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
code, pre, kbd, samp, [data-testid="stCode"] code {
    font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
}

/* App background — subtle radial gradient */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 700px at 80% -10%, rgba(247,147,26,0.12), transparent 60%),
        radial-gradient(900px 500px at -10% 30%, rgba(124,58,237,0.06), transparent 60%),
        var(--bg-0);
}
[data-testid="stHeader"] { background: transparent; }

/* Block container — give it some breathing room */
[data-testid="stMain"] .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px;
}

/* ── Hero card ──────────────────────────────────────────────────────────────── */
.cc-hero {
    background:
        linear-gradient(135deg, rgba(247,147,26,0.10), rgba(124,58,237,0.06)),
        rgba(255,255,255,0.85);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 18px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(26,26,46,0.06);
}
.cc-hero-title {
    display: flex; align-items: center; gap: 14px;
    font-size: 1.85rem; font-weight: 800; color: var(--text);
    letter-spacing: -0.02em; margin: 0;
}
.cc-hero-title .chain-icon {
    font-size: 1.6rem;
    background: linear-gradient(135deg, var(--btc), var(--btc-2));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 8px rgba(247,147,26,0.3));
}
.cc-hero-subtitle {
    color: var(--muted); font-size: 0.88rem; margin-top: 4px;
    font-weight: 400;
}

/* Live indicator — pulsing green dot */
.cc-live {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 999px;
    background: rgba(46,204,113,0.12);
    border: 1px solid rgba(46,204,113,0.35);
    color: var(--green); font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.cc-live .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 0 0 rgba(46,204,113,0.7);
    animation: pulse 2s infinite;
}
.cc-live.stale {
    background: rgba(231,76,60,0.12);
    border-color: rgba(231,76,60,0.35);
    color: var(--red);
}
.cc-live.stale .dot { background: var(--red); animation: none; }
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0   rgba(46,204,113,0.7); }
    70%  { box-shadow: 0 0 0 10px rgba(46,204,113,0); }
    100% { box-shadow: 0 0 0 0   rgba(46,204,113,0); }
}

/* Hero info chips */
.cc-chips {
    display: flex; flex-wrap: wrap; gap: 10px;
    margin-top: 14px;
}
.cc-chip {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 8px;
    background: #ffffff; border: 1px solid var(--border);
    font-size: 0.82rem; color: var(--text);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 2px rgba(26,26,46,0.04);
}
.cc-chip:hover {
    border-color: var(--btc);
    box-shadow: 0 2px 8px rgba(247,147,26,0.15);
}
.cc-chip .label { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
.cc-chip .value { font-family: 'JetBrains Mono', monospace; color: var(--text); font-weight: 600; }
.cc-chip.height .value { color: var(--btc-2); }

/* ── Metric cards (st.metric) ───────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(26,26,46,0.04);
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: var(--btc);
    box-shadow: 0 8px 24px rgba(247,147,26,0.12);
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    color: var(--muted) !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    letter-spacing: -0.01em;
    line-height: 1.1 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    gap: 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}
[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 18px !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s ease, background 0.15s ease;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: var(--text) !important;
    background: rgba(247,147,26,0.06) !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--btc-2) !important;
    border-bottom: 2px solid var(--btc) !important;
    background: rgba(247,147,26,0.10) !important;
    font-weight: 600 !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border);
    box-shadow: 1px 0 0 rgba(26,26,46,0.02);
}
[data-testid="stSidebar"] h2 {
    background: linear-gradient(135deg, var(--btc), var(--btc-2));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}

/* ── Code blocks ────────────────────────────────────────────────────────────── */
[data-testid="stCode"] {
    border: 1px solid var(--border);
    border-radius: 10px;
    background: #f8f9fc !important;
}
[data-testid="stCode"] pre { background: transparent !important; }
[data-testid="stCode"] code, [data-testid="stCode"] pre, [data-testid="stCode"] span {
    color: #1a1a2e !important;
}

/* ── Dataframes ─────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
}

/* ── Headings ───────────────────────────────────────────────────────────────── */
h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -0.01em; }
h3 { font-weight: 700 !important; }
hr { border-color: var(--border) !important; opacity: 0.6; }

/* ── Body text — override Streamlit defaults for legibility ─────────────────── */
[data-testid="stMain"], [data-testid="stMain"] p, [data-testid="stMain"] li,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span {
    color: var(--text) !important;
}

/* Captions (st.caption) */
[data-testid="stCaptionContainer"], small, .stCaption,
[data-testid="stMarkdownContainer"] small {
    color: var(--muted) !important;
    font-size: 0.82rem !important;
}

/* Form labels — sliders, toggles, selects, number inputs */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
label, [data-baseweb="form-control"] label,
[data-testid="stMarkdownContainer"] strong {
    color: var(--text) !important;
    font-weight: 500 !important;
}
[data-testid="stWidgetLabel"] p { font-size: 0.88rem !important; }

/* Slider min/max ticks and values */
[data-testid="stSlider"] [data-baseweb="slider"] div,
[data-testid="stSlider"] span { color: var(--text) !important; }

/* Selectbox / number input values */
[data-baseweb="select"] div, [data-baseweb="input"] input {
    color: var(--text) !important;
}
[data-baseweb="input"] input { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; }

/* Inline code (e.g. `mempool.space`) inside markdown */
[data-testid="stMarkdownContainer"] code, p code, li code, td code {
    background: rgba(247,147,26,0.10) !important;
    color: var(--btc-2) !important;
    border: 1px solid rgba(247,147,26,0.25);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.86em;
}

/* Tables inside markdown */
[data-testid="stMarkdownContainer"] table {
    border-collapse: collapse;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    width: 100%;
    margin: 8px 0;
    background: #ffffff;
}
[data-testid="stMarkdownContainer"] th {
    background: var(--bg-3);
    color: var(--text) !important;
    font-weight: 600;
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
}
[data-testid="stMarkdownContainer"] td {
    color: var(--text) !important;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    background: #ffffff;
}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background: #fafbfd; }

/* Info / Success / Warning / Error boxes */
[data-testid="stAlert"] {
    border-radius: 10px;
    border: 1px solid var(--border);
    padding: 12px 16px !important;
    background: #ffffff !important;
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"],
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
    color: var(--text) !important;
}
/* Info (blue tint) */
[data-testid="stAlert"][data-baseweb="notification"] {
    background: #f0f6ff !important;
    border-color: rgba(37,99,235,0.3) !important;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    box-shadow: 0 1px 2px rgba(26,26,46,0.04);
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p {
    color: var(--text) !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
    color: var(--text) !important;
}

/* Sidebar text */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
    color: var(--text) !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--muted) !important;
}

/* Dataframe header / cell colors */
[data-testid="stDataFrame"] [role="columnheader"] {
    background: var(--bg-3) !important;
    color: var(--text) !important;
    font-weight: 600 !important;
}
[data-testid="stDataFrame"] [role="gridcell"] {
    color: var(--text) !important;
    background: #ffffff;
}

/* Plotly chart background — already transparent in module code,
   but ensure surrounding container blends in */
[data-testid="stPlotlyChart"] { background: transparent; }

/* ── Buttons ────────────────────────────────────────────────────────────────── */
.stButton button, .stDownloadButton button {
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    background: #ffffff !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color: var(--btc) !important;
    background: rgba(247,147,26,0.08) !important;
    color: var(--btc-2) !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-0); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted-2); }

/* ── Footer ─────────────────────────────────────────────────────────────────── */
.cc-footer {
    margin-top: 40px;
    padding: 16px 0;
    border-top: 1px solid var(--border);
    color: var(--muted-2);
    font-size: 0.78rem;
    text-align: center;
}
.cc-footer a { color: var(--muted); text-decoration: none; }
.cc-footer a:hover { color: var(--btc); }

/* ── Hide Streamlit branding ────────────────────────────────────────────────── */
#MainMenu, [data-testid="stStatusWidget"] { visibility: hidden; }
footer { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⛓️ CryptoChain")
    st.caption("Live Bitcoin cryptographic metrics")
    st.markdown(
        '<div style="margin-top:-6px; font-size:0.78rem; color:#5a5a78;">'
        'Source: <a href="https://mempool.space/docs/api" target="_blank" '
        'style="color:#d97a05; text-decoration:none; font-weight:500;">mempool.space</a></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**⚙️ Controls**")
    n_blocks = st.slider("Blocks to fetch", min_value=20, max_value=200, value=50, step=10,
                          help="Used by M1 (PoW), M4 (AI), M5 (Merkle) and M6 (Security).")
    auto_refresh = st.toggle("Auto-refresh (60 s)", value=True,
                              help="Re-fetches the latest blocks every minute.")

    st.divider()
    st.markdown(
        '<div style="font-size:0.85rem; color:#1a1a2e;"><b>Alejandro Déniz Solana</b></div>'
        '<div style="font-size:0.75rem; color:#5a5a78; margin-top:2px;">'
        'UAX · Cryptography 2025-26<br/>Prof. Jorge Calvo</div>'
        '<div style="margin-top:10px;">'
        '<a href="https://github.com/aledeniiz/blockchain-dashboard-aledeniiz" target="_blank" '
        'style="color:#5a5a78; font-size:0.78rem; text-decoration:none; font-weight:500;">↗ View on GitHub</a></div>',
        unsafe_allow_html=True,
    )

# ── Fetch data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_blocks(n: int):
    return get_blocks(n)

with st.spinner("Fetching live Bitcoin data…"):
    try:
        blocks = load_blocks(n_blocks)
        fetch_ok = True
    except Exception as e:
        st.error(f"API error: {e}. Retrying in 30 s…")
        fetch_ok = False
        blocks = []

# ── Hero ───────────────────────────────────────────────────────────────────────
if blocks:
    latest = blocks[-1]
    age_s  = max(0, int(time.time() - latest["timestamp"]))
    age_str = f"{age_s // 60} min {age_s % 60:02d} s ago" if age_s >= 60 else f"{age_s} s ago"
    is_stale = age_s > 30 * 60   # >30 min without a block is unusual
    live_class = "stale" if is_stale else ""
    live_text = "STALE" if is_stale else "LIVE"
    hash_short = latest["id"][:14] + "…" + latest["id"][-6:]

    st.markdown(f"""
<div class="cc-hero">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
    <div>
      <div class="cc-hero-title">
        <span class="chain-icon">⛓️</span>
        <span>CryptoChain Analyzer</span>
      </div>
      <div class="cc-hero-subtitle">Real-time Bitcoin cryptographic metrics · SHA-256 verification · AI anomaly detection</div>
    </div>
    <span class="cc-live {live_class}"><span class="dot"></span> {live_text}</span>
  </div>
  <div class="cc-chips">
    <span class="cc-chip height"><span class="label">Block</span><span class="value">#{latest['height']:,}</span></span>
    <span class="cc-chip"><span class="label">Hash</span><span class="value">{hash_short}</span></span>
    <span class="cc-chip"><span class="label">Txs</span><span class="value">{latest['tx_count']:,}</span></span>
    <span class="cc-chip"><span class="label">Found</span><span class="value">{age_str}</span></span>
    <span class="cc-chip"><span class="label">Now</span><span class="value">{time.strftime('%H:%M:%S UTC', time.gmtime())}</span></span>
  </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div class="cc-hero">
  <div class="cc-hero-title"><span class="chain-icon">⛓️</span><span>CryptoChain Analyzer</span></div>
  <div class="cc-hero-subtitle">Awaiting block data — check your network connection.</div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⛏️  M1 · Proof of Work",
    "🔍  M2 · Block Header",
    "📈  M3 · Difficulty History",
    "🤖  M4 · AI Anomaly Detector",
    "🌳  M5 · Merkle Proof",
    "🛡️  M6 · Security Score",
])

with tab1: m1_pow.render(blocks)
with tab2: m2_header.render(blocks)
with tab3: m3_difficulty.render()
with tab4: m4_ai.render(blocks)
with tab5: m5_merkle.render(blocks)
with tab6: m6_security.render(blocks)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cc-footer">
  Built with <a href="https://streamlit.io" target="_blank">Streamlit</a> &nbsp;·&nbsp;
  Data from <a href="https://mempool.space" target="_blank">mempool.space</a> &nbsp;·&nbsp;
  <a href="https://github.com/aledeniiz/blockchain-dashboard-aledeniiz" target="_blank">Source on GitHub</a>
  &nbsp;·&nbsp; Cryptography 2025-26 · UAX
</div>
""", unsafe_allow_html=True)

# ── Auto-refresh ───────────────────────────────────────────────────────────────
if auto_refresh and fetch_ok:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
