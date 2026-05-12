"""
modules/m7_predictor.py  —  M7 (optional): Second AI approach

Difficulty predictor — supervised regression over historical epoch data.

Why this is a meaningfully different AI approach from M4:
  - M4 (Isolation Forest): unsupervised, tree-based, anomaly detection
  - M7 (Linear / Ridge regression): supervised, linear, time-series forecasting

Both work on Bitcoin data but answer different questions:
  - M4: "is this block statistically unusual?"  (classification flavor)
  - M7: "what will the next difficulty adjustment be?"  (regression)

We model log(difficulty) because Bitcoin difficulty has grown roughly
exponentially with hashrate over the last decade, so log-space is the
appropriate domain for a linear model.

Reference: this is the "Predictor" option (#1) listed in the assignment PDF.
"""

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from modules.m3_difficulty import fetch_difficulty_history


# ── feature engineering ────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a per-epoch feature row to predict the *next* epoch's difficulty.

    Features at epoch t (only data observable at the end of epoch t):
      - epoch_idx       : monotonic index (captures secular growth trend)
      - log_diff        : log10 of current difficulty
      - ratio           : actual_avg_time / target_time (drives the retarget)
      - log_diff_lag1   : log10 of previous epoch's difficulty
      - log_diff_diff1  : log10(diff_t) - log10(diff_{t-1})  (recent momentum)

    Target:
      - log_diff_next   : log10 of the *next* epoch's difficulty
    """
    d = df.sort_values("timestamp").reset_index(drop=True).copy()
    d["log_diff"]       = np.log10(d["difficulty"])
    d["log_diff_lag1"]  = d["log_diff"].shift(1)
    d["log_diff_diff1"] = d["log_diff"] - d["log_diff_lag1"]
    d["epoch_idx"]      = np.arange(len(d), dtype=float)
    d["log_diff_next"]  = d["log_diff"].shift(-1)
    # ratio may have NaNs at the open epoch (no end timestamp yet) → fill
    d["ratio"] = d["ratio"].fillna(1.0)
    return d


# ── modelling ──────────────────────────────────────────────────────────────────

def train_and_evaluate(d: pd.DataFrame):
    """
    Train two models (linear + random forest), evaluate them, return predictions.
    Test split = last 25 % of rows (chronological — never random for time series).
    """
    feat_cols = ["epoch_idx", "log_diff", "ratio", "log_diff_lag1", "log_diff_diff1"]
    train_df  = d.dropna(subset=feat_cols + ["log_diff_next"])
    if len(train_df) < 6:
        return None  # not enough history

    X = train_df[feat_cols].values
    y = train_df["log_diff_next"].values

    n_test = max(2, int(round(len(train_df) * 0.25)))
    X_train, X_test = X[:-n_test], X[-n_test:]
    y_train, y_test = y[:-n_test], y[-n_test:]

    models = {
        "Linear regression":    LinearRegression(),
        "Ridge (α=1.0)":    Ridge(alpha=1.0),
        "Random forest (100)":  RandomForestRegressor(n_estimators=100, random_state=42),
    }

    results = {}
    for name, mdl in models.items():
        mdl.fit(X_train, y_train)
        yhat_test = mdl.predict(X_test)
        yhat_all  = mdl.predict(X)
        mae_log = mean_absolute_error(y_test, yhat_test)
        # MAPE in raw difficulty space — what matters operationally
        mape    = np.mean(np.abs(10**yhat_test - 10**y_test) / 10**y_test) * 100
        r2      = r2_score(y_test, yhat_test) if len(y_test) >= 2 else float("nan")
        results[name] = dict(model=mdl, yhat_all=yhat_all,
                             mae_log=mae_log, mape=mape, r2=r2,
                             n_train=len(X_train), n_test=len(X_test))

    # Also predict the *future* difficulty (no observed target yet) — use the last
    # complete row as the input
    last = d.dropna(subset=feat_cols).iloc[-1:][feat_cols].values
    future_predictions = {name: 10 ** float(r["model"].predict(last)[0])
                          for name, r in results.items()}

    return results, train_df, future_predictions, feat_cols


# ── render ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=900)   # difficulty history is slow to fetch — cache 15 min
def _fetch_history(n_periods: int) -> pd.DataFrame:
    return fetch_difficulty_history(n_periods)


def render(blocks: list):
    st.markdown("### \U0001F52E Difficulty Predictor (M7 — second AI approach)")
    st.caption("Supervised regression on historical epoch data. Different "
               "model family than M4 — see report for comparison.")

    n_periods = st.slider(
        "Epochs of history to use (1 epoch = 2 016 blocks ≈ 2 weeks)",
        min_value=10, max_value=30, value=20, step=2,
        help="More history = more training data, but the model assumes the "
             "growth regime is stationary."
    )

    with st.spinner(f"Fetching {n_periods} epochs of difficulty history…"):
        try:
            df = _fetch_history(n_periods)
        except Exception as e:
            st.error(f"API error: {e}")
            return

    if df is None or len(df) < 6:
        st.warning("Not enough epoch data fetched to train a regression model.")
        return

    feats = build_features(df)
    out = train_and_evaluate(feats)
    if out is None:
        st.warning("Could not build a training set with the current data.")
        return
    results, train_df, future_predictions, feat_cols = out

    # ── KPI cards ──────────────────────────────────────────────────────────────
    # Use the linear model as the headline pick (interpretable, fewer assumptions
    # — random forest is shown alongside)
    linear = results["Linear regression"]
    current_diff = train_df.iloc[-1]["difficulty"]
    pred_next    = future_predictions["Linear regression"]
    delta_pct    = (pred_next / current_diff - 1.0) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current difficulty",    f"{current_diff/1e12:.2f} T")
    c2.metric("Predicted next epoch",  f"{pred_next/1e12:.2f} T",
              delta=f"{delta_pct:+.2f}%")
    c3.metric("MAE (log10 space)",     f"{linear['mae_log']:.4f}",
              help="Mean absolute error of log10(difficulty) on the held-out test split.")
    c4.metric("Test R²",          f"{linear['r2']:+.3f}",
              help="Coefficient of determination on test split. 1.0 = perfect.")

    st.divider()

    # ── Actual vs predicted plot ───────────────────────────────────────────────
    st.markdown("#### Actual vs Predicted difficulty (log₁₀ scale)")
    fig = go.Figure()
    x = train_df["timestamp"]
    y_true = train_df["log_diff_next"]
    fig.add_trace(go.Scatter(
        x=x, y=y_true,
        mode="lines+markers", name="Actual next-epoch difficulty",
        line=dict(color="#1a1a2e", width=2),
        marker=dict(size=7, color="#1a1a2e"),
    ))
    palette = {
        "Linear regression":   "#F7931A",
        "Ridge (α=1.0)":  "#9b6bff",
        "Random forest (100)": "#2563eb",
    }
    for name, r in results.items():
        fig.add_trace(go.Scatter(
            x=x, y=r["yhat_all"],
            mode="lines", name=name,
            line=dict(color=palette[name], width=2, dash="dash"),
        ))

    # Shade test region
    n_test = linear["n_test"]
    if n_test > 0 and len(x) > n_test:
        x_start = x.iloc[-n_test]
        fig.add_vrect(
            x0=x_start, x1=x.iloc[-1],
            fillcolor="rgba(247,147,26,0.08)", line_width=0,
            annotation_text="Test split", annotation_position="top left",
            annotation_font_color="#d97a05",
        )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#1a1a2e"),
        xaxis=dict(title="Epoch start date", gridcolor="#e3e4ec"),
        yaxis=dict(title="log₁₀(difficulty)", gridcolor="#e3e4ec"),
        legend=dict(orientation="h"),
        margin=dict(t=10, b=40),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Metrics table ──────────────────────────────────────────────────────────
    st.markdown("#### Model comparison")
    rows = []
    for name, r in results.items():
        rows.append({
            "Model":          name,
            "MAE (log10)":    f"{r['mae_log']:.4f}",
            "MAPE (raw %)":   f"{r['mape']:.2f}%",
            "R² (test)": f"{r['r2']:+.3f}",
            "Train rows":     r["n_train"],
            "Test rows":      r["n_test"],
            "Next-epoch pred. (T)": f"{future_predictions[name]/1e12:.2f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Theory + caveats ───────────────────────────────────────────────────────
    with st.expander("\U0001F4D6 Method and caveats"):
        st.markdown(f"""
**Why log-space.** Bitcoin difficulty has grown roughly exponentially with hash
rate (~10¹⁸ H/s today vs ~10⁶ H/s in 2010). A *linear* model in
log₁₀(difficulty) is the right baseline; in raw space the same model
would systematically under-predict the upper tail.

**Features.** `epoch_idx` captures the long-term secular trend; `ratio` (actual
average block time ÷ 600 s in the current epoch) directly drives the
2-016-block retarget rule and is therefore the strongest one-step predictor;
`log_diff_lag1` and `log_diff_diff1` add short-term momentum.

**Train/test split.** Chronological (last 25 % of rows = test). Random shuffles
are invalid for time-series because they leak future information into training.

**Evaluation.**
- *MAE on log10*: scale-invariant error in the model's working space.
- *MAPE on raw difficulty*: operational error (what fraction off is the predicted
  next-epoch difficulty?).
- *R²*: variance explained on the test split. With only ~{linear['n_test']}
  test points it has high variance; treat it as a sanity check, not gospel.

**Comparison with M4.** M4 is *unsupervised* tree-ensemble (Isolation Forest)
detecting anomalies in inter-block times. M7 is *supervised* linear / ensemble
regression forecasting the next adjustment value. Different problems, different
tools — the two together cover the two main flavours of ML applied to
blockchain data.

**Limitations.**
- Difficulty is set by a deterministic rule, so the residual error comes from
  hashrate noise; with only {linear['n_train']} training rows the variance is
  large.
- The model assumes the growth regime is stationary; a major regime shift
  (China mining ban 2021, halving cycles) would invalidate the fit.
- We are *not* trying to predict price or hashrate — only difficulty.
""")
