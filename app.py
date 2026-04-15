"""
app.py — CryptoChain Analyzer Dashboard
Entry point. Run with: streamlit run app.py

Architecture:
  - Fetches live Bitcoin data from Blockstream API (no API key needed)
  - Auto-refreshes every 60 seconds using st.rerun()
  - Modules M1–M4 are in the modules/ directory
  - API client is in api/blockchain_client.py
"""

import time
import streamlit as st

from api.blockchain_client import get_blocks, get_latest_block
from modules import m1_pow, m2_header, m3_difficulty, m4_ai

st.set_page_config(
    page_title="CryptoChain Analyzer",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("⛓️ CryptoChain Analyzer")
st.sidebar.markdown(
    "**Live Bitcoin cryptographic metrics**  \n"
    "Data source: [Blockstream API](https://blockstream.info/api)"
)

n_blocks = st.sidebar.slider("Blocks to fetch (M1/M4)", min_value=20, max_value=200, value=50, step=10)
auto_refresh = st.sidebar.toggle("Auto-refresh (60s)", value=True)
refresh_interval = 60  # seconds

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Alejandro Déniz Solana**  \n"
    "UAX Cryptography 2025–26  \n"
    "Prof. Jorge Calvo"
)

# ── Fetch data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_blocks(n: int):
    return get_blocks(n)

with st.spinner("Fetching live Bitcoin data..."):
    try:
        blocks = load_blocks(n_blocks)
        fetch_ok = True
    except Exception as e:
        st.error(f"API error: {e}. Retrying in 30s...")
        fetch_ok = False
        blocks = []

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⛓️ CryptoChain Analyzer Dashboard")
if blocks:
    latest = blocks[-1]
    st.caption(
        f"Latest block: **#{latest['height']}** — "
        f"Hash: `{latest['id'][:20]}...` — "
        f"Updated: {time.strftime('%H:%M:%S')}"
    )

st.markdown("---")

# ── Module tabs ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "M1 · Proof of Work",
    "M2 · Block Header",
    "M3 · Difficulty History",
    "M4 · AI Anomaly Detector",
])

with tab1:
    m1_pow.render(blocks)

with tab2:
    m2_header.render(blocks)

with tab3:
    m3_difficulty.render()

with tab4:
    m4_ai.render(blocks)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh and fetch_ok:
    time.sleep(refresh_interval)
    st.cache_data.clear()
    st.rerun()
