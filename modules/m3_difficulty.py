"""
modules/m3_difficulty.py
M3 — Difficulty History

Bitcoin adjusts its difficulty every 2016 blocks (~2 weeks) so that
the average block time stays at 600 seconds.

Adjustment formula (Section 6.1 of Bitcoin whitepaper):
  new_difficulty = old_difficulty * (actual_time / target_time)
  where target_time = 2016 * 600 = 1,209,600 seconds (2 weeks)
  Capped: adjustment is limited to a factor of 4 in either direction.

This module:
  1. Fetches blocks at each difficulty adjustment height to build history.
  2. Plots difficulty over time.
  3. Marks each adjustment event.
  4. Shows ratio = actual_block_time / 600s for each period.
"""

import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import BASE_URL, bits_to_difficulty

ADJUSTMENT_PERIOD = 2016   # blocks per difficulty epoch
TARGET_BLOCK_TIME = 600    # seconds


def fetch_difficulty_history(n_periods: int = 10) -> pd.DataFrame:
    """
    Fetch the first block of the last n_periods difficulty epochs.
    Returns a DataFrame with columns:
      height, timestamp, bits, difficulty, actual_block_time, ratio
    """
    # Get current height
    tip_height = int(requests.get(f"{BASE_URL}/blocks/tip/height", timeout=10).text.strip())

    # Compute adjustment heights (heights that are multiples of 2016)
    current_epoch_start = (tip_height // ADJUSTMENT_PERIOD) * ADJUSTMENT_PERIOD
    heights = [current_epoch_start - i * ADJUSTMENT_PERIOD for i in range(n_periods)]
    heights = [h for h in heights if h >= 0]
    heights.sort()

    rows = []
    for height in heights:
        url = f"{BASE_URL}/block-height/{height}"
        block_hash = requests.get(url, timeout=10).text.strip()
        block = requests.get(f"{BASE_URL}/block/{block_hash}", timeout=10).json()

        # Get the LAST block of this epoch (height + 2015) for actual time calculation
        end_height = height + ADJUSTMENT_PERIOD - 1
        end_hash_resp = requests.get(f"{BASE_URL}/block-height/{end_height}", timeout=10)
        if end_hash_resp.status_code == 200:
            end_hash = end_hash_resp.text.strip()
            end_block = requests.get(f"{BASE_URL}/block/{end_hash}", timeout=10).json()
            actual_time = end_block["timestamp"] - block["timestamp"]
        else:
            actual_time = None

        difficulty = bits_to_difficulty(block["bits"])
        avg_block_time = (actual_time / ADJUSTMENT_PERIOD) if actual_time else None
        ratio = (avg_block_time / TARGET_BLOCK_TIME) if avg_block_time else None

        rows.append({
            "height": height,
            "timestamp": pd.Timestamp(block["timestamp"], unit="s"),
            "bits": block["bits"],
            "difficulty": difficulty,
            "actual_total_seconds": actual_time,
            "avg_block_time_s": avg_block_time,
            "ratio": ratio,
        })

    return pd.DataFrame(rows)


def render(df: pd.DataFrame | None = None):
    """Render M3 panel in Streamlit."""
    st.subheader("M3 · Difficulty History")

    n_periods = st.slider("Number of difficulty epochs", min_value=5, max_value=20, value=10)

    if df is None or len(df) < 2:
        with st.spinner(f"Fetching {n_periods} difficulty epochs (one API call per epoch)..."):
            try:
                df = fetch_difficulty_history(n_periods)
            except Exception as e:
                st.error(f"Error fetching difficulty history: {e}")
                return

    # --- Difficulty over time ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["difficulty"] / 1e12,
        mode="lines+markers",
        name="Difficulty (T)",
        line=dict(color="#F7931A", width=2),
        marker=dict(size=8, symbol="circle"),
    ))

    # Mark adjustment events
    for _, row in df.iterrows():
        fig.add_vline(
            x=row["timestamp"].timestamp() * 1000,
            line=dict(color="rgba(255,255,255,0.2)", dash="dot"),
        )

    fig.update_layout(
        title="Bitcoin Difficulty over Time (per 2016-block epoch)",
        xaxis_title="Date",
        yaxis_title="Difficulty (Tera)",
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Ratio actual/target block time ---
    df_ratio = df.dropna(subset=["ratio"])
    if not df_ratio.empty:
        fig2 = go.Figure()
        colors = ["#2ecc71" if r <= 1 else "#e74c3c" for r in df_ratio["ratio"]]
        fig2.add_trace(go.Bar(
            x=df_ratio["timestamp"],
            y=df_ratio["ratio"],
            marker_color=colors,
            name="Actual/Target time ratio",
        ))
        fig2.add_hline(y=1.0, line=dict(color="white", dash="dash"), annotation_text="Target (1.0 = 600s)")
        fig2.update_layout(
            title="Ratio: Actual avg block time / 600s per epoch (green=faster, red=slower)",
            xaxis_title="Epoch start date",
            yaxis_title="Ratio",
            template="plotly_dark",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Data table ---
    display_df = df[["height", "timestamp", "difficulty", "avg_block_time_s", "ratio"]].copy()
    display_df["difficulty"] = (display_df["difficulty"] / 1e12).round(2).astype(str) + " T"
    display_df["avg_block_time_s"] = display_df["avg_block_time_s"].apply(
        lambda x: f"{x:.0f}s ({x/60:.1f} min)" if x else "—"
    )
    display_df["ratio"] = display_df["ratio"].apply(lambda x: f"{x:.3f}" if x else "—")
    display_df.columns = ["Epoch height", "Date", "Difficulty", "Avg block time", "Ratio vs 600s"]
    st.dataframe(display_df, use_container_width=True)

    with st.expander("Difficulty adjustment formula"):
        st.markdown(
            """
            Every **2016 blocks** (~2 weeks), Bitcoin nodes recalculate the difficulty:

            ```
            new_difficulty = old_difficulty × (2_016 × 600) / actual_time_seconds
            ```

            The adjustment is **capped at ×4 or ÷4** to prevent extreme jumps.
            If miners found blocks too fast (ratio < 1), difficulty increases.
            If too slow (ratio > 1), difficulty decreases.
            """
        )
