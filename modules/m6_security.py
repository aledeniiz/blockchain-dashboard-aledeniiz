"""
modules/m6_security.py  —  M6 (optional): Bitcoin Security Score

Two analyses:

1. **51 % attack cost** — what it would cost (USD/hour) for an adversary to
   match the current network hash rate, both via electricity opex on owned
   ASICs and via rented hash power.

2. **Confirmation-depth attack probability** — Nakamoto §11 formula.
   Given an attacker holding fraction q of the network hash power, compute
   the probability that they catch up after z confirmations:

       λ = z · q / p,   p = 1 − q
       P = 1 − Σ_{k=0..z} (λ^k · e^-λ / k!) · (1 − (q/p)^(z−k))

   When q ≥ 0.5 the chain is no longer secure and P = 1.

Reference: Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash
System.* Section 11 — Calculations.
"""

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import bits_to_difficulty


# ── helpers ────────────────────────────────────────────────────────────────────

def estimate_hashrate_ths(difficulty: float) -> float:
    """Network hash rate in TH/s from current difficulty."""
    return difficulty * (2 ** 32) / 600 / 1e12


def attack_success_probability(q: float, z: int) -> float:
    """
    Nakamoto §11. Probability the attacker overtakes the honest chain after z
    confirmations when controlling fraction q of the hash power (0 < q < 0.5).
    Returns 1.0 for q >= 0.5.
    """
    if q >= 0.5:
        return 1.0
    if q <= 0.0:
        return 0.0
    p = 1.0 - q
    lam = z * q / p
    total = 0.0
    for k in range(z + 1):
        poisson = math.exp(-lam) * (lam ** k) / math.factorial(k)
        total += poisson * (1.0 - (q / p) ** (z - k))
    return max(0.0, min(1.0, 1.0 - total))


# ── render ─────────────────────────────────────────────────────────────────────

def render(blocks: list):
    st.markdown("### 🛡️ Bitcoin Security Score")
    st.caption("Live cost of a 51 % attack and Nakamoto §11 confirmation-depth probabilities.")

    if not blocks:
        st.warning("No block data available.")
        return

    latest = blocks[-1]
    difficulty = bits_to_difficulty(latest["bits"])
    hashrate_ths = estimate_hashrate_ths(difficulty)
    hashrate_eh  = hashrate_ths / 1e6              # EH/s
    hashrate_ph  = hashrate_ths / 1e3              # PH/s

    # ── parameters ─────────────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Attack parameters")
    p1, p2, p3 = st.columns(3)
    with p1:
        kwh_price = st.number_input("Electricity price ($/kWh)",
                                     min_value=0.01, max_value=0.50,
                                     value=0.06, step=0.01, format="%.2f")
    with p2:
        efficiency_j_per_th = st.number_input("ASIC efficiency (J / TH)",
                                               min_value=10.0, max_value=80.0,
                                               value=17.5, step=0.5,
                                               help="Antminer S21 ≈ 17.5 J/TH; older S19 ≈ 30 J/TH")
    with p3:
        rental_per_ph_hour = st.number_input("Rental price ($ / PH·hour)",
                                              min_value=0.10, max_value=50.0,
                                              value=5.0, step=0.5,
                                              help="Approximate NiceHash SHA-256 rental rate")

    asic_th_per_unit  = 200.0     # Antminer S21 class
    asic_unit_price   = 3500.0    # USD per unit (rough market average)

    # ── 51 % attack cost ───────────────────────────────────────────────────────
    # To >50 %, attacker needs at least the same hash rate as the current network.
    attacker_th = hashrate_ths

    # Operating cost (electricity only, owned ASICs)
    power_w     = attacker_th * efficiency_j_per_th     # J/s = W
    power_kw    = power_w / 1000.0
    elec_cost_h = power_kw * kwh_price                  # $/hour

    # Rental cost (NiceHash-style)
    rental_cost_h = (attacker_th / 1e3) * rental_per_ph_hour   # PH * $/PH·h

    # Capex
    asic_count  = attacker_th / asic_th_per_unit
    asic_capex  = asic_count * asic_unit_price

    st.markdown("#### 💰 Cost to match 100 % of the current network")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Network Hash Rate", f"{hashrate_eh:.0f} EH/s")
    c2.metric("Electricity / hour", f"${elec_cost_h/1e6:.2f} M")
    c3.metric("Rental / hour",      f"${rental_cost_h/1e6:.2f} M")
    c4.metric("ASIC capex (one-shot)", f"${asic_capex/1e9:.1f} B")

    st.info(
        f"To control 51 % of mining, an attacker needs roughly **{asic_count/1e6:.2f} M** "
        f"top-tier ASICs drawing **{power_kw/1e6:.1f} GW** — comparable to a "
        f"medium-sized country's electricity demand. The rental market alone cannot "
        f"deliver this magnitude continuously."
    )

    # cost breakdown bar chart
    fig_cost = go.Figure()
    fig_cost.add_trace(go.Bar(
        x=["Electricity / hour", "Rental / hour", "ASIC capex"],
        y=[elec_cost_h, rental_cost_h, asic_capex],
        marker_color=["#F7931A", "#2ecc71", "#3498db"],
        text=[f"${elec_cost_h/1e6:.2f} M",
              f"${rental_cost_h/1e6:.2f} M",
              f"${asic_capex/1e9:.2f} B"],
        textposition="outside",
    ))
    fig_cost.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,26,0.8)",
        yaxis=dict(title="USD (log scale)", type="log", gridcolor="#2d2d4e"),
        xaxis=dict(gridcolor="#2d2d4e"),
        margin=dict(t=30, b=40),
        height=300,
        showlegend=False,
    )
    st.plotly_chart(fig_cost, use_container_width=True)

    st.divider()

    # ── Nakamoto §11 ───────────────────────────────────────────────────────────
    st.markdown("#### 🎯 Confirmation-depth attack probability — Nakamoto §11")
    st.caption(
        "Probability that an attacker holding fraction *q* of total hash power "
        "ever catches up after *z* confirmations. Under q < 0.5 the probability "
        "decays exponentially with z."
    )

    q_share = st.slider("Attacker's hash-power share q",
                         min_value=0.05, max_value=0.49,
                         value=0.30, step=0.01,
                         format="%.2f")

    z_values = list(range(0, 16))
    probs    = [attack_success_probability(q_share, z) for z in z_values]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=z_values, y=probs,
        mode="lines+markers",
        name=f"q = {q_share:.2f}",
        line=dict(color="#e74c3c", width=2.5),
        marker=dict(size=8, color="#e74c3c"),
        hovertemplate="z = %{x}<br>P(attack succeeds) = %{y:.4%}<extra></extra>",
    ))

    # comparison curves at q = 0.10 / 0.20 / 0.40
    palette = {0.10: "#2ecc71", 0.20: "#3498db", 0.40: "#9b59b6"}
    for q_ref, color in palette.items():
        fig.add_trace(go.Scatter(
            x=z_values,
            y=[attack_success_probability(q_ref, z) for z in z_values],
            mode="lines",
            name=f"q = {q_ref:.2f}",
            line=dict(color=color, width=1.2, dash="dot"),
            hovertemplate=f"q={q_ref:.2f}<br>z = %{{x}}<br>P = %{{y:.4%}}<extra></extra>",
        ))

    fig.add_hline(y=0.001,
                  line=dict(color="white", dash="dash", width=1),
                  annotation_text="0.1 %", annotation_font_color="#aaa")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,26,0.8)",
        xaxis=dict(title="Confirmations (z)", gridcolor="#2d2d4e"),
        yaxis=dict(title="P(attacker catches up)", type="log",
                   gridcolor="#2d2d4e", tickformat=".0%"),
        legend=dict(orientation="h"),
        margin=dict(t=10, b=40),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # numeric table
    df = pd.DataFrame({
        "z (confirmations)": z_values,
        f"P (q = {q_share:.2f})": [f"{p:.6%}" for p in probs],
    })
    st.dataframe(df, use_container_width=True, hide_index=True, height=260)

    # six-confirmation rule explanation
    p6 = attack_success_probability(q_share, 6)
    st.markdown(
        f"With **q = {q_share:.0%}** and the canonical **6-confirmation rule**, "
        f"the probability the attacker still catches up is **{p6:.4%}** "
        f"({'≈ ' + f'1 in {1/p6:,.0f}' if p6 > 0 else 'effectively zero'})."
    )

    # ── theory ─────────────────────────────────────────────────────────────────
    with st.expander("📖 Method & references"):
        st.markdown("""
**51 % attack cost.** Network hash rate is derived from current difficulty as
`H ≈ difficulty · 2³² / 600`. Operating cost is `H · efficiency · $/kWh`.
Rental cost uses approximate NiceHash SHA-256 quotes per PH·hour. Capex is the
number of top-class ASICs (200 TH/s, ~$3 500) needed to match the network.

**Nakamoto §11 formula.** For an attacker with hash-power fraction *q* and
honest miners *p = 1 − q*, the expected attacker progress after *z* honest
blocks is `λ = z · q / p`. The probability they ever overtake is

\\[ P = 1 - \\sum_{k=0}^{z} \\frac{\\lambda^k e^{-\\lambda}}{k!} \\left[ 1 - \\left(\\frac{q}{p}\\right)^{z-k} \\right] \\]

For *q ≥ 0.5* the random walk has non-negative drift so *P = 1*.

**Reference:** Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash
System*. Section 11.
""")
