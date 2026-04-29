"""
app.py — CryptoChain Analyzer Dashboard
Entry point. Run with: streamlit run app.py
"""

import time
import streamlit as st

from api.blockchain_client import get_blocks, get_latest_block
from modules import m1_pow, m2_header, m3_difficulty, m4_ai, m5_merkle

st.set_page_config(
    page_title="CryptoChain Analyzer",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Metric cards */
[data-testid="stMetric"] {
    background: #1a1a2e;
    border: 1px solid #2d2d4e;
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { font-size: 0.78rem; color: #9b9bbf; letter-spacing: 0.05em; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 700; color: #f0f0f0; }

/* Tab styling */
[data-testid="stTab"] button { font-size: 0.9rem; font-weight: 500; }

/* Code blocks */
[data-testid="stCode"] { border-radius: 8px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0f0f1a; border-right: 1px solid #2d2d4e; }

/* Dividers */
hr { border-color: #2d2d4e !important; }

/* Bitcoin orange accent */
.btc-accent { color: #F7931A; font-weight: 700; }

/* Section headers */
h3 { color: #e0e0e0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⛓️ CryptoChain Analyzer")
    st.caption("Live Bitcoin cryptographic metrics")
    st.markdown("**Source:** [mempool.space API](https://mempool.space/api)")
    st.divider()

    n_blocks = st.slider("Blocks to fetch (M1 / M4)", min_value=20, max_value=200, value=50, step=10)
    auto_refresh = st.toggle("Auto-refresh (60 s)", value=True)

    st.divider()
    st.markdown("**Alejandro Déniz Solana**")
    st.caption("UAX · Criptografía 2025–26")
    st.caption("Prof. Jorge Calvo")

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

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_info = st.columns([3, 2])
with col_title:
    st.markdown("# ⛓️ CryptoChain Analyzer")

if blocks:
    latest = blocks[-1]
    with col_info:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"**Block** `#{latest['height']:,}`&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"Hash `{latest['id'][:16]}…`&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"🕐 {time.strftime('%H:%M:%S')}",
            unsafe_allow_html=True,
        )

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⛏️  M1 · Proof of Work",
    "🔍  M2 · Block Header",
    "📈  M3 · Difficulty History",
    "🤖  M4 · AI Anomaly Detector",
    "🌳  M5 · Merkle Proof",
])

with tab1:
    m1_pow.render(blocks)

with tab2:
    m2_header.render(blocks)

with tab3:
    m3_difficulty.render()

with tab4:
    m4_ai.render(blocks)

with tab5:
    m5_merkle.render(blocks)

# ── Auto-refresh ───────────────────────────────────────────────────────────────
if auto_refresh and fetch_ok:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
