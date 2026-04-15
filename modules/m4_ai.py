"""
modules/m4_ai.py
M4 — AI Component: Anomaly Detector for inter-block times

Model choice: Isolation Forest (scikit-learn)
Why: Isolation Forest is well-suited for unsupervised anomaly detection on
univariate/multivariate time series without requiring labeled data.
It isolates anomalies by randomly selecting a feature and a split value;
anomalous points (far from the bulk) require fewer splits to isolate.

Data: Inter-arrival times (seconds) between consecutive Bitcoin blocks.
Expected baseline: Exponential(λ = 1/600s).
Deviations may indicate:
  - Mining pool coordinated block withholding
  - Network propagation delays / partitions
  - Orphan chain events
  - Natural statistical outliers

Evaluation metric:
  - Contamination rate (fraction of blocks flagged as anomalous)
  - Anomaly score distribution vs. inter-block time
  - Visual comparison: anomalous vs. normal blocks on time series
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def compute_features(blocks: list) -> pd.DataFrame:
    """
    Compute features for anomaly detection from a list of block dicts.
    Features per block:
      - inter_time_s : seconds since previous block
      - log_inter_time : log(inter_time_s + 1)  — stabilises variance
      - tx_count : number of transactions
    """
    blocks_sorted = sorted(blocks, key=lambda b: b["height"])
    rows = []
    for i in range(1, len(blocks_sorted)):
        prev = blocks_sorted[i - 1]
        curr = blocks_sorted[i]
        inter_time = curr["timestamp"] - prev["timestamp"]
        rows.append({
            "height": curr["height"],
            "timestamp": pd.Timestamp(curr["timestamp"], unit="s"),
            "inter_time_s": inter_time,
            "log_inter_time": np.log1p(inter_time),
            "tx_count": curr.get("tx_count", 0),
        })
    return pd.DataFrame(rows)


def run_isolation_forest(df: pd.DataFrame, contamination: float = 0.05):
    """
    Train Isolation Forest on inter-block time features.
    contamination: expected fraction of anomalies (default 5%).
    Returns df with added columns: anomaly_score, is_anomaly.
    """
    features = ["log_inter_time", "tx_count"]
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X_scaled)

    df = df.copy()
    df["anomaly_score"] = -model.score_samples(X_scaled)  # higher = more anomalous
    df["is_anomaly"] = model.predict(X_scaled) == -1      # True = anomaly

    return df, model, scaler


def render(blocks: list):
    """Render M4 panel in Streamlit."""
    st.subheader("M4 · AI Anomaly Detector — Inter-block Time Analysis")

    if len(blocks) < 10:
        st.warning("Need at least 10 blocks for anomaly detection.")
        return

    contamination = st.slider(
        "Contamination rate (expected % of anomalies)",
        min_value=0.01, max_value=0.20, value=0.05, step=0.01,
        format="%.2f"
    )

    df = compute_features(blocks)
    df, model, scaler = run_isolation_forest(df, contamination)

    n_anomalies = df["is_anomaly"].sum()
    st.markdown(
        f"Analyzed **{len(df)} block intervals** — "
        f"flagged **{n_anomalies}** anomalies ({n_anomalies/len(df)*100:.1f}%)"
    )

    # --- Inter-block time series with anomalies highlighted ---
    fig = go.Figure()
    normal = df[~df["is_anomaly"]]
    anomalous = df[df["is_anomaly"]]

    fig.add_trace(go.Scatter(
        x=normal["timestamp"], y=normal["inter_time_s"] / 60,
        mode="markers", name="Normal",
        marker=dict(color="#2ecc71", size=5, opacity=0.7),
    ))
    fig.add_trace(go.Scatter(
        x=anomalous["timestamp"], y=anomalous["inter_time_s"] / 60,
        mode="markers", name="Anomaly",
        marker=dict(color="#e74c3c", size=10, symbol="x"),
    ))
    fig.add_hline(y=10, line=dict(color="white", dash="dash"),
                  annotation_text="Target: 10 min")
    fig.update_layout(
        title="Inter-block times — Anomalies highlighted in red (Isolation Forest)",
        xaxis_title="Time",
        yaxis_title="Inter-block time (minutes)",
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Anomaly score distribution ---
    fig2 = px.histogram(
        df, x="inter_time_s", color="is_anomaly",
        nbins=30,
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        labels={"inter_time_s": "Inter-block time (s)", "is_anomaly": "Anomaly"},
        title="Distribution of inter-block times (red = flagged as anomaly)",
        barmode="overlay",
    )
    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # --- Top anomalies table ---
    st.markdown("#### Most anomalous blocks")
    top = df.sort_values("anomaly_score", ascending=False).head(10)
    top_display = top[["height", "timestamp", "inter_time_s", "tx_count", "anomaly_score"]].copy()
    top_display["inter_time_s"] = top_display["inter_time_s"].apply(lambda x: f"{x:.0f}s ({x/60:.1f} min)")
    top_display["anomaly_score"] = top_display["anomaly_score"].round(4)
    top_display.columns = ["Height", "Timestamp", "Inter-block time", "Tx count", "Anomaly score"]
    st.dataframe(top_display, use_container_width=True)

    with st.expander("Model details — Isolation Forest"):
        st.markdown(
            f"""
            **Model:** Isolation Forest (sklearn, n_estimators=100, contamination={contamination:.2f})

            **Features used:**
            - `log_inter_time`: log(inter_block_seconds + 1) — stabilises the heavy tail of the exponential
            - `tx_count`: number of transactions in the block

            **Why Isolation Forest?**
            No labeled data is needed. The algorithm isolates points that are easy to separate
            from the bulk — anomalies (unusually fast or slow blocks) require fewer random
            splits than typical blocks clustered around 10 minutes.

            **Evaluation:** Contamination rate set to {contamination:.0%}.
            The expected baseline distribution is Exponential(λ=1/600s). Any block with
            an inter-arrival time that is a statistical outlier relative to this distribution
            gets a high anomaly score.

            **Limitation:** With only {len(df)} samples, the model may flag legitimate
            outliers from the exponential tail as anomalies. A larger dataset (1000+ blocks)
            would yield more reliable estimates.
            """
        )
