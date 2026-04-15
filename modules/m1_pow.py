"""
modules/m1_pow.py
M1 — Proof of Work Monitor

Displays:
  1. Current Bitcoin difficulty and its visual representation as a leading-zero
     threshold in the 256-bit SHA-256 space.
  2. Distribution of inter-block times for the last N blocks.
     Expected distribution: Exponential(lambda=1/600s) — because block arrivals
     follow a Poisson process (each hash attempt succeeds independently with
     constant probability). The memoryless property of the exponential distribution
     means the time until the next block does not depend on how long we've waited.
  3. Estimated current network hash rate.
     Formula: hash_rate ≈ difficulty * 2^32 / 600  (hashes/second)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from api.blockchain_client import get_blocks, bits_to_difficulty


def leading_zero_bits(block_hash: str) -> int:
    """Count leading zero bits in a hex-encoded block hash."""
    value = int(block_hash, 16)
    if value == 0:
        return 256
    return 256 - value.bit_length()


def estimate_hashrate(difficulty: float) -> float:
    """
    Estimate network hash rate in hashes/second.
    Each block requires on average difficulty * 2^32 hash attempts.
    Target block time is 600 seconds.
    hash_rate = difficulty * 2^32 / 600
    """
    return difficulty * (2 ** 32) / 600


def render(blocks: list):
    """Render M1 panel in Streamlit."""
    st.subheader("M1 · Proof of Work Monitor")

    if not blocks:
        st.warning("No block data available.")
        return

    latest = blocks[-1]
    difficulty = bits_to_difficulty(latest["bits"])
    hashrate = estimate_hashrate(difficulty)
    leading_zeros = leading_zero_bits(latest["id"])

    # --- KPI row ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Difficulty", f"{difficulty/1e12:.2f} T")
    col2.metric("Est. Hash Rate", f"{hashrate/1e18:.2f} EH/s")
    col3.metric("Leading zero bits", f"{leading_zeros} bits")

    # --- Difficulty threshold visualisation ---
    st.markdown(
        f"""
        **What the difficulty means in SHA-256 space:**
        The current target requires the 256-bit block hash to have at least
        **{leading_zeros} leading zero bits**.
        That means the valid hash space is 1 / 2^{leading_zeros} of all possible
        256-bit values ≈ {1 / (2**leading_zeros):.2e} of the total space.
        """
    )

    # --- Inter-block time distribution ---
    st.markdown("#### Inter-block time distribution (last {} blocks)".format(len(blocks)))
    timestamps = [b["timestamp"] for b in blocks]
    timestamps.sort()
    inter_times = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    inter_times_min = [t / 60 for t in inter_times]

    fig = px.histogram(
        x=inter_times_min,
        nbins=30,
        labels={"x": "Inter-block time (minutes)", "y": "Count"},
        title="Inter-block time distribution — expected: Exponential(λ=1/10 min)",
        color_discrete_sequence=["#F7931A"],
    )
    # Overlay theoretical exponential PDF
    x_range = np.linspace(0, max(inter_times_min) * 1.1, 200)
    lambda_param = 1 / 10  # 1 per 10 minutes
    pdf = lambda_param * np.exp(-lambda_param * x_range) * len(inter_times_min) * (max(inter_times_min) / 30)
    fig.add_trace(go.Scatter(x=x_range, y=pdf, mode="lines",
                             name="Exp(λ=1/10 min) theoretical",
                             line=dict(color="white", dash="dash")))
    fig.update_layout(template="plotly_dark", legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Why exponential distribution?"):
        st.markdown(
            """
            Bitcoin mining is a Bernoulli process: each hash attempt succeeds with
            probability p = 1/difficulty × 2^32. With ~10^18 attempts per second
            network-wide, the number of attempts until success follows a geometric
            distribution, which in continuous time converges to an **Exponential(λ)**
            distribution with λ = 1/600 seconds. This means block arrivals form a
            **Poisson process** — they are memoryless and independent.
            """
        )

    # --- Recent blocks table ---
    df = pd.DataFrame([{
        "Height": b["height"],
        "Hash (first 16)": b["id"][:16] + "...",
        "Leading 0-bits": leading_zero_bits(b["id"]),
        "Tx count": b["tx_count"],
        "Timestamp": pd.Timestamp(b["timestamp"], unit="s"),
    } for b in reversed(blocks[-10:])])
    st.dataframe(df, use_container_width=True)
