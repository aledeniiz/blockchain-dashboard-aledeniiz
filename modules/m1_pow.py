"""
modules/m1_pow.py  —  M1: Proof of Work Monitor
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from api.blockchain_client import bits_to_difficulty


# ── helpers ────────────────────────────────────────────────────────────────────

def leading_zero_bits(block_hash: str) -> int:
    value = int(block_hash, 16)
    return 256 - value.bit_length() if value else 256


def estimate_hashrate(difficulty: float) -> float:
    """hash_rate ≈ difficulty × 2³² / 600  (H/s)"""
    return difficulty * (2 ** 32) / 600


# ── render ─────────────────────────────────────────────────────────────────────

def render(blocks: list):
    if not blocks:
        st.warning("No block data available.")
        return

    latest = blocks[-1]
    difficulty = bits_to_difficulty(latest["bits"])
    hashrate   = estimate_hashrate(difficulty)
    lz_bits    = leading_zero_bits(latest["id"])

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("### ⛏️ Current Network Status")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Block",      f"#{latest['height']:,}")
    c2.metric("Difficulty",        f"{difficulty/1e12:.2f} T")
    c3.metric("Est. Hash Rate",    f"{hashrate/1e18:.0f} EH/s")
    c4.metric("Leading Zero Bits", f"{lz_bits} bits")

    st.divider()

    # ── PoW explanation ────────────────────────────────────────────────────────
    st.info(
        f"**What this means:** The current target requires the 256-bit block hash to start with "
        f"at least **{lz_bits} leading zero bits** — i.e. the valid hash space is "
        f"**1 / 2^{lz_bits}** ≈ {1/(2**lz_bits):.2e} of all possible hashes. "
        f"Miners computed ~{hashrate/1e18:.0f} EH/s to find it."
    )

    # ── Inter-block time histogram ─────────────────────────────────────────────
    st.markdown("### ⏱️ Inter-block Time Distribution")
    st.caption(f"Last {len(blocks)} blocks — expected distribution: Exponential(λ = 1/10 min)")

    timestamps = sorted(b["timestamp"] for b in blocks)
    inter_min  = [(timestamps[i+1] - timestamps[i]) / 60 for i in range(len(timestamps) - 1)]

    fig = go.Figure()

    # Histogram bars
    fig.add_trace(go.Histogram(
        x=inter_min,
        nbinsx=30,
        name="Observed blocks",
        marker_color="#F7931A",
        opacity=0.85,
        hovertemplate="Time: %{x:.1f} min<br>Count: %{y}<extra></extra>",
    ))

    # Theoretical Exp(λ=1/10) overlay
    x_th = np.linspace(0, max(inter_min) * 1.05, 300)
    lam  = 1 / 10
    pdf  = lam * np.exp(-lam * x_th) * len(inter_min) * (max(inter_min) / 30)
    fig.add_trace(go.Scatter(
        x=x_th, y=pdf,
        mode="lines",
        name="Exp(λ=1/10 min) — theoretical",
        line=dict(color="#1a1a2e", width=2, dash="dash"),
        hovertemplate="Time: %{x:.1f} min<br>PDF: %{y:.1f}<extra></extra>",
    ))

    fig.add_vline(x=10, line=dict(color="#2ecc71", dash="dot", width=1.5),
                  annotation_text="Target: 10 min", annotation_font_color="#2ecc71")

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#1a1a2e"),
        legend=dict(orientation="h", yanchor="top", y=0.99, xanchor="right", x=0.99),
        xaxis=dict(title="Inter-block time (minutes)", gridcolor="#e3e4ec"),
        yaxis=dict(title="Block count", gridcolor="#e3e4ec"),
        margin=dict(t=20, b=40),
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Why the exponential distribution?"):
        st.markdown("""
Each hash attempt succeeds with probability **p = 1 / (difficulty × 2³²)**.
With ~10¹⁸ attempts/second network-wide, the number of attempts until success
follows a **Geometric(p)** distribution, which in continuous time converges to
**Exponential(λ = 1/600 s)**.

Key property: **memorylessness** — the expected time to the next block does not
depend on how long we have already waited. Block arrivals form a **Poisson process**.
        """)

    # ── Recent blocks table ────────────────────────────────────────────────────
    st.markdown("### 🧱 Recent Blocks")
    rows = [{
        "Height":          f"#{b['height']:,}",
        "Hash prefix":     b["id"][:20] + "…",
        "Leading 0-bits":  leading_zero_bits(b["id"]),
        "Tx count":        f"{b['tx_count']:,}",
        "Timestamp (UTC)": pd.Timestamp(b["timestamp"], unit="s").strftime("%Y-%m-%d %H:%M"),
    } for b in reversed(blocks[-12:])]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
