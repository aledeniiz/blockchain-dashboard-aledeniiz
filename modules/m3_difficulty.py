"""
modules/m3_difficulty.py  —  M3: Difficulty History
Adjustment every 2016 blocks (~2 weeks): new_diff = old_diff × (target_time / actual_time).
"""

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import BASE_URL, bits_to_difficulty

ADJUSTMENT_PERIOD = 2016
TARGET_TIME       = 600   # seconds


# ── data fetching ──────────────────────────────────────────────────────────────

def fetch_difficulty_history(n_periods: int = 10) -> pd.DataFrame:
    tip = int(requests.get(f"{BASE_URL}/blocks/tip/height", timeout=15).text.strip())
    current_epoch = (tip // ADJUSTMENT_PERIOD) * ADJUSTMENT_PERIOD
    heights = sorted([current_epoch - i * ADJUSTMENT_PERIOD
                      for i in range(n_periods) if current_epoch - i * ADJUSTMENT_PERIOD >= 0])

    rows = []
    for h in heights:
        bh  = requests.get(f"{BASE_URL}/block-height/{h}", timeout=15).text.strip()
        blk = requests.get(f"{BASE_URL}/block/{bh}", timeout=15).json()

        # epoch end block for actual time
        end_h  = h + ADJUSTMENT_PERIOD - 1
        end_r  = requests.get(f"{BASE_URL}/block-height/{end_h}", timeout=15)
        actual = None
        if end_r.status_code == 200:
            eb      = requests.get(f"{BASE_URL}/block/{end_r.text.strip()}", timeout=15).json()
            actual  = eb["timestamp"] - blk["timestamp"]

        diff     = bits_to_difficulty(blk["bits"])
        avg_time = actual / ADJUSTMENT_PERIOD if actual else None
        ratio    = avg_time / TARGET_TIME if avg_time else None

        rows.append({
            "height":        h,
            "timestamp":     pd.Timestamp(blk["timestamp"], unit="s"),
            "difficulty":    diff,
            "avg_block_s":   avg_time,
            "ratio":         ratio,
            "change_pct":    None,
        })

    df = pd.DataFrame(rows)
    df["change_pct"] = df["difficulty"].pct_change() * 100
    return df


# ── render ─────────────────────────────────────────────────────────────────────

def render(df: pd.DataFrame | None = None):
    # ── controls ───────────────────────────────────────────────────────────────
    st.markdown("### 📈 Difficulty Adjustment History")
    n_periods = st.slider("Epochs to display (1 epoch = 2 016 blocks ≈ 2 weeks)",
                          min_value=5, max_value=20, value=10)

    if df is None or len(df) < 2:
        with st.spinner(f"Fetching {n_periods} epochs from mempool.space…"):
            try:
                df = fetch_difficulty_history(n_periods)
            except Exception as e:
                st.error(f"Error: {e}")
                return

    latest = df.iloc[-1]

    # ── KPIs ───────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Difficulty",  f"{latest['difficulty']/1e12:.2f} T")
    c2.metric("Epoch Start Block",   f"#{int(latest['height']):,}")
    if pd.notna(latest["avg_block_s"]) and latest["avg_block_s"]:
        c3.metric("Avg Block Time",  f"{latest['avg_block_s']:.0f} s  ({latest['avg_block_s']/60:.1f} min)")
    else:
        c3.metric("Avg Block Time", "Epoch in progress")
    if pd.notna(latest["change_pct"]):
        delta_str = f"{latest['change_pct']:+.2f}%"
        c4.metric("Last Adjustment", delta_str,
                  delta=delta_str,
                  delta_color="inverse" if latest["change_pct"] < 0 else "normal")

    st.divider()

    # ── difficulty line chart ──────────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["difficulty"] / 1e12,
        mode="lines+markers",
        name="Difficulty (T)",
        line=dict(color="#F7931A", width=2.5),
        marker=dict(size=9, color="#F7931A", line=dict(color="#fff", width=1.5)),
        fill="tozeroy",
        fillcolor="rgba(247,147,26,0.08)",
        hovertemplate="<b>%{x|%b %d %Y}</b><br>Difficulty: %{y:.2f} T<extra></extra>",
    ))

    # Adjustment markers
    for _, row in df.iterrows():
        fig.add_vline(
            x=row["timestamp"].timestamp() * 1000,
            line=dict(color="rgba(255,255,255,0.12)", dash="dot", width=1),
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,26,0.8)",
        xaxis=dict(title="Date", gridcolor="#2d2d4e"),
        yaxis=dict(title="Difficulty (Tera)", gridcolor="#2d2d4e"),
        legend=dict(orientation="h"),
        margin=dict(t=10, b=40),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── ratio bar chart ────────────────────────────────────────────────────────
    df_r = df.dropna(subset=["ratio"])
    if not df_r.empty:
        colors = ["#2ecc71" if r <= 1 else "#e74c3c" for r in df_r["ratio"]]
        fig2   = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_r["timestamp"],
            y=df_r["ratio"],
            marker_color=colors,
            name="Actual / Target time",
            hovertemplate=(
                "<b>%{x|%b %d %Y}</b><br>"
                "Ratio: %{y:.3f}<br>"
                "<i>< 1 → faster (↑ diff)  |  > 1 → slower (↓ diff)</i>"
                "<extra></extra>"
            ),
        ))
        fig2.add_hline(y=1.0,
                       line=dict(color="white", dash="dash", width=1.5),
                       annotation_text="Target: 10 min/block",
                       annotation_font_color="#ffffff")
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,15,26,0.8)",
            xaxis=dict(title="Epoch start date", gridcolor="#2d2d4e"),
            yaxis=dict(title="Actual time / 600 s", gridcolor="#2d2d4e"),
            margin=dict(t=10, b=40),
            height=280,
        )
        st.caption("🟢 Green = blocks found faster than 10 min (difficulty will rise)  ·  🔴 Red = slower (difficulty will drop)")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── data table ─────────────────────────────────────────────────────────────
    st.markdown("### 🗒️ Epoch Summary")
    disp = df[["height", "timestamp", "difficulty", "avg_block_s", "ratio", "change_pct"]].copy()
    disp["difficulty"]   = (disp["difficulty"] / 1e12).round(3).astype(str) + " T"
    disp["avg_block_s"]  = disp["avg_block_s"].apply(lambda x: f"{x:.0f} s ({x/60:.1f} min)" if x else "—")
    disp["ratio"]        = disp["ratio"].apply(lambda x: f"{x:.3f}" if x else "—")
    disp["change_pct"]   = disp["change_pct"].apply(lambda x: f"{x:+.2f}%" if x and not pd.isna(x) else "—")
    disp["height"]       = disp["height"].apply(lambda x: f"#{int(x):,}")
    disp["timestamp"]    = disp["timestamp"].dt.strftime("%Y-%m-%d")
    disp.columns = ["Epoch start", "Date", "Difficulty", "Avg block time", "Ratio", "Δ vs prev epoch"]
    st.dataframe(disp, use_container_width=True, hide_index=True)

    with st.expander("📖 Difficulty adjustment formula"):
        st.markdown("""
Every **2 016 blocks** (~2 weeks) every full node recalculates:

```
new_difficulty = old_difficulty × (2016 × 600) / actual_seconds
```

**Constraints:** adjustment is capped at **×4** (max harder) and **÷4** (max easier)
to prevent extreme swings from a sudden hashrate change.

- Ratio < 1 → blocks came faster than 10 min → difficulty **increases**
- Ratio > 1 → blocks came slower than 10 min → difficulty **decreases**
        """)
