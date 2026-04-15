"""
modules/m4_ai.py  —  M4: AI Anomaly Detector
Isolation Forest on inter-block times.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ── ML pipeline ────────────────────────────────────────────────────────────────

def compute_features(blocks: list) -> pd.DataFrame:
    blocks_sorted = sorted(blocks, key=lambda b: b["height"])
    rows = []
    for i in range(1, len(blocks_sorted)):
        prev, curr = blocks_sorted[i - 1], blocks_sorted[i]
        dt = curr["timestamp"] - prev["timestamp"]
        rows.append({
            "height":        curr["height"],
            "timestamp":     pd.Timestamp(curr["timestamp"], unit="s"),
            "inter_time_s":  dt,
            "log_inter":     np.log1p(dt),
            "tx_count":      curr.get("tx_count", 0),
        })
    return pd.DataFrame(rows)


def run_model(df: pd.DataFrame, contamination: float):
    X = df[["log_inter", "tx_count"]].fillna(0).values
    scaler = StandardScaler()
    Xs     = scaler.fit_transform(X)
    model  = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
    model.fit(Xs)
    df = df.copy()
    df["score"]      = -model.score_samples(Xs)
    df["is_anomaly"] = model.predict(Xs) == -1
    return df, model, scaler


# ── render ─────────────────────────────────────────────────────────────────────

def render(blocks: list):
    if len(blocks) < 10:
        st.warning("Need at least 10 blocks for anomaly detection.")
        return

    # ── controls ───────────────────────────────────────────────────────────────
    st.markdown("### 🤖 Isolation Forest — Inter-block Time Anomalies")
    st.caption("Unsupervised anomaly detection on inter-block timing. No labeled data required.")

    contamination = st.slider(
        "Contamination rate (expected fraction of anomalies)",
        min_value=0.01, max_value=0.20, value=0.05, step=0.01,
        format="%.2f",
        help="Set to the approximate % of blocks you expect to be anomalous.",
    )

    df, model, scaler = run_model(compute_features(blocks), contamination)

    n_total    = len(df)
    n_anom     = int(df["is_anomaly"].sum())
    pct        = n_anom / n_total * 100
    mean_time  = df["inter_time_s"].mean()
    median_time = df["inter_time_s"].median()

    # ── KPIs ───────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Intervals Analyzed",   f"{n_total}")
    c2.metric("Anomalies Flagged",     f"{n_anom}  ({pct:.1f}%)")
    c3.metric("Mean Inter-block Time", f"{mean_time:.0f} s  ({mean_time/60:.1f} min)")
    c4.metric("Median",                f"{median_time:.0f} s  ({median_time/60:.1f} min)")

    st.divider()

    # ── time series scatter ────────────────────────────────────────────────────
    normal = df[~df["is_anomaly"]]
    anom   = df[ df["is_anomaly"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=normal["timestamp"], y=normal["inter_time_s"] / 60,
        mode="markers", name="Normal",
        marker=dict(color="#2ecc71", size=6, opacity=0.7,
                    line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="<b>Block #%{customdata}</b><br>Time: %{y:.1f} min<extra></extra>",
        customdata=normal["height"],
    ))
    fig.add_trace(go.Scatter(
        x=anom["timestamp"], y=anom["inter_time_s"] / 60,
        mode="markers", name="Anomaly",
        marker=dict(color="#e74c3c", size=12, symbol="x",
                    line=dict(color="#ff6b6b", width=2)),
        hovertemplate="<b>Block #%{customdata}</b><br>Time: %{y:.1f} min<br><b>ANOMALY</b><extra></extra>",
        customdata=anom["height"],
    ))
    fig.add_hline(y=10, line=dict(color="#F7931A", dash="dot", width=1.5),
                  annotation_text="Target: 10 min", annotation_font_color="#F7931A")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,26,0.8)",
        xaxis=dict(title="Time (UTC)", gridcolor="#2d2d4e"),
        yaxis=dict(title="Inter-block time (minutes)", gridcolor="#2d2d4e"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=10, b=40),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── distribution histogram ─────────────────────────────────────────────────
    st.markdown("#### Distribution of Inter-block Times")
    fig2 = px.histogram(
        df, x="inter_time_s", color="is_anomaly",
        nbins=35,
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        labels={"inter_time_s": "Inter-block time (s)", "is_anomaly": "Anomaly"},
        barmode="overlay",
        opacity=0.8,
    )

    # Theoretical Exp overlay
    x_th  = np.linspace(0, df["inter_time_s"].max() * 1.05, 300)
    lam   = 1 / 600
    bin_w = df["inter_time_s"].max() / 35
    pdf   = lam * np.exp(-lam * x_th) * n_total * bin_w
    fig2.add_trace(go.Scatter(
        x=x_th, y=pdf,
        mode="lines",
        name="Exp(λ=1/600 s) theoretical",
        line=dict(color="white", width=2, dash="dash"),
    ))
    fig2.add_vline(x=600, line=dict(color="#F7931A", dash="dot", width=1.5),
                   annotation_text="600 s", annotation_font_color="#F7931A")
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,26,0.8)",
        legend=dict(orientation="h"),
        xaxis=dict(gridcolor="#2d2d4e"),
        yaxis=dict(title="Count", gridcolor="#2d2d4e"),
        margin=dict(t=10, b=40),
        height=300,
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── top anomalies table ────────────────────────────────────────────────────
    st.markdown("### 🚨 Most Anomalous Blocks")
    top = df.sort_values("score", ascending=False).head(10).copy()
    top["inter_time_s"] = top["inter_time_s"].apply(lambda x: f"{x:.0f} s  ({x/60:.1f} min)")
    top["score"]        = top["score"].round(4)
    top["height"]       = top["height"].apply(lambda x: f"#{int(x):,}")
    top["timestamp"]    = top["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    top["tx_count"]     = top["tx_count"].apply(lambda x: f"{int(x):,}")
    top.rename(columns={
        "height": "Block", "timestamp": "Time (UTC)",
        "inter_time_s": "Inter-block time", "tx_count": "Txs",
        "score": "Anomaly score",
    }, inplace=True)
    st.dataframe(
        top[["Block", "Time (UTC)", "Inter-block time", "Txs", "Anomaly score"]],
        use_container_width=True, hide_index=True,
    )

    # ── model details ──────────────────────────────────────────────────────────
    with st.expander("📖 Model details — Isolation Forest"):
        st.markdown(f"""
**Algorithm:** Isolation Forest (`sklearn`, n_estimators=100, contamination={contamination:.2f})

**Why Isolation Forest?**
No labeled data is needed. The model isolates points by randomly selecting a feature
and a random split value. Anomalies (unusually fast or slow blocks) sit far from the
bulk of the data and are isolated in **fewer splits** — hence a higher anomaly score.

**Features:**
| Feature | Description |
|---------|-------------|
| `log_inter` | log(inter_block_seconds + 1) — stabilises the heavy tail of the exponential |
| `tx_count`  | number of transactions — unusually empty or full blocks are more suspicious |

**Baseline:** Bitcoin inter-block times follow **Exponential(λ = 1/600 s)** because
mining is a memoryless Poisson process. Any block deviating significantly from this
baseline receives a high isolation score.

**Limitation:** With only {n_total} intervals, the model may flag legitimate
tail events. A dataset of 1 000+ blocks yields more stable estimates.
        """)
