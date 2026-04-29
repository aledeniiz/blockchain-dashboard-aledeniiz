"""
report/build_report.py
Generates the 2-3 page final report (`report.pdf`) using reportlab.
Run with: python report/build_report.py
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


OUT_PATH = Path(__file__).parent / "report.pdf"


# ── styles ─────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="ReportTitle",
    parent=styles["Title"],
    fontSize=18, leading=22, spaceAfter=4, textColor=colors.HexColor("#1a1a2e"),
))
styles.add(ParagraphStyle(
    name="ReportSubtitle",
    parent=styles["Normal"],
    fontSize=10, leading=14, textColor=colors.HexColor("#555"),
    spaceAfter=14, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="H2",
    parent=styles["Heading2"],
    fontSize=13, leading=16, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor("#F7931A"),
))
styles.add(ParagraphStyle(
    name="Body",
    parent=styles["BodyText"],
    fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Mono",
    parent=styles["Code"],
    fontSize=8.5, leading=11, leftIndent=10, textColor=colors.HexColor("#222"),
    backColor=colors.HexColor("#f4f4f8"),
    borderPadding=4, borderColor=colors.HexColor("#ddd"), borderWidth=0.5,
))
styles.add(ParagraphStyle(
    name="Caption",
    parent=styles["Normal"],
    fontSize=8.5, leading=11, textColor=colors.HexColor("#777"),
    spaceAfter=10, alignment=TA_LEFT,
))


_cell_style = ParagraphStyle(
    name="Cell",
    parent=styles["BodyText"],
    fontSize=9, leading=11, spaceAfter=0, spaceBefore=0,
)
_cell_header_style = ParagraphStyle(
    name="CellHeader",
    parent=styles["BodyText"],
    fontSize=9, leading=11, spaceAfter=0, spaceBefore=0,
    fontName="Helvetica-Bold", textColor=colors.white,
)


def _wrap_cells(data):
    """Wrap each cell in a Paragraph so inline markup and word-wrap work."""
    out = []
    for r, row in enumerate(data):
        wrapped = []
        for cell in row:
            style = _cell_header_style if r == 0 else _cell_style
            wrapped.append(Paragraph(str(cell), style))
        out.append(wrapped)
    return out


def make_table(data, col_widths=None):
    t = Table(_wrap_cells(data), colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f7f7fa")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


# ── content ────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        title="CryptoChain Analyzer Dashboard — Final Report",
        author="Alejandro Déniz Solana",
    )
    flow = []

    # ── header ────────────────────────────────────────────────────────────────
    flow.append(Paragraph("CryptoChain Analyzer Dashboard", styles["ReportTitle"]))
    flow.append(Paragraph(
        "Final Report &nbsp;·&nbsp; Cryptography and Cybersecurity (UAX, 2025-26) &nbsp;·&nbsp; "
        "Prof. Jorge Calvo<br/>"
        "Author: <b>Alejandro Déniz Solana</b> "
        "(<font color='#F7931A'>@aledeniiz</font>) &nbsp;·&nbsp; "
        "Repo: <i>github.com/aledeniiz/blockchain-dashboard-aledeniiz</i>",
        styles["ReportSubtitle"],
    ))

    # ── section 1: cryptographic metrics ──────────────────────────────────────
    flow.append(Paragraph("1. Cryptographic metrics displayed", styles["H2"]))
    flow.append(Paragraph(
        "The dashboard pulls live data from the public mempool.space REST API "
        "(with a Blockstream fallback) and exposes six cryptographic metrics "
        "directly tied to the theory of Topic 7. Every metric is recomputed "
        "from primitives using Python's <font face='Courier'>hashlib</font> "
        "and the standard library — no third-party crypto package is trusted "
        "for the verification step.",
        styles["Body"],
    ))

    metrics_table = [
        ["Module", "Metric", "Theoretical link"],
        ["M1", "Difficulty, leading-zero bits, hash rate",
              "Proof of Work; difficulty = genesis_target / target"],
        ["M1", "Inter-block time histogram",
              "Exp(λ = 1/600 s) — mining is a memoryless Poisson process"],
        ["M2", "80-byte header parse + manual SHA256² check",
              "PoW validity: SHA256(SHA256(header)) < target"],
        ["M2", "Compact 'bits' decoding into 256-bit target",
              "T = coefficient × 256^(exponent − 3)"],
        ["M3", "Difficulty per epoch, ratio actual/600 s",
              "Retarget every 2 016 blocks"],
        ["M5", "Merkle path verification (optional)",
              "Inclusion proof in O(log<sub>2</sub> n) hashes"],
        ["M6", "51 % attack cost, Nakamoto §11 attack probability (optional)",
              "Random-walk gambler's-ruin model of catch-up"],
    ]
    flow.append(make_table(metrics_table, col_widths=[1.7*cm, 6.3*cm, 8.4*cm]))
    flow.append(Spacer(1, 0.3*cm))

    flow.append(Paragraph(
        "The header verification (M2) is the most important sanity check: for "
        "any block the dashboard fetches its raw 80-byte header, parses each "
        "little-endian field with <font face='Courier'>struct</font>, computes "
        "<font face='Courier'>SHA256(SHA256(header))</font>, reverses the byte "
        "order, decodes the target from the 'bits' field, and confirms that "
        "the resulting 256-bit integer is strictly below the target. The same "
        "block hash printed on any explorer is reproduced byte-for-byte from "
        "first principles — closing the loop between theory and live data.",
        styles["Body"],
    ))

    # ── section 2: AI component ───────────────────────────────────────────────
    flow.append(Paragraph("2. AI component (M4) — Isolation Forest", styles["H2"]))
    flow.append(Paragraph(
        "<b>Why this model.</b> Bitcoin inter-block times are a memoryless "
        "Poisson arrival process, so the inter-arrival distribution is "
        "Exponential(λ = 1/600 s). Detecting blocks that deviate from this "
        "distribution is an unsupervised problem: there are no ground-truth "
        "anomaly labels available. Isolation Forest is a natural fit because "
        "(i) it does not require labels, (ii) it scales linearly in the number "
        "of samples, and (iii) it isolates outliers in fewer random splits than "
        "inliers, which matches the geometric intuition of an exponential tail.",
        styles["Body"],
    ))
    flow.append(Paragraph(
        "<b>Features.</b> "
        "<font face='Courier'>log_inter = log(inter_block_seconds + 1)</font> "
        "stabilises the heavy tail of the exponential, and "
        "<font face='Courier'>tx_count</font> contributes a secondary signal "
        "(unusually empty or full blocks may co-occur with timing anomalies). "
        "Features are standardised with <font face='Courier'>StandardScaler</font> "
        "before being fed to <font face='Courier'>IsolationForest"
        "(n_estimators=100, contamination=c, random_state=42)</font>, where "
        "<i>c</i> is exposed as a slider to the user.",
        styles["Body"],
    ))
    flow.append(Paragraph(
        "<b>Evaluation.</b> The unsupervised setting precludes accuracy/F1, so "
        "the dashboard reports two complementary diagnostics. (1) The empirical "
        "histogram of inter-block times is overlaid with the theoretical "
        "Exp(λ = 1/600 s) PDF: the body of the distribution should match and "
        "the tail should hold the flagged anomalies. (2) The fraction of blocks "
        "flagged at the chosen contamination rate is reported alongside a "
        "scatter plot of inter-block time vs. wall-clock time, so the user can "
        "visually confirm the model is selecting the longest gaps. On a "
        "50-block window pulled at the time of writing, the model flagged the "
        "expected number of tail events; on a 200-block window the signal-to-"
        "noise ratio improves further. <b>Limitations.</b> With a small block "
        "window the contamination parameter is non-trivial to choose; with a "
        "large window the assumption of a stationary λ becomes weaker because "
        "the 2 016-block retarget changes the rate. Both are documented in the "
        "module's expander.",
        styles["Body"],
    ))

    # ── section 3: optional modules ───────────────────────────────────────────
    flow.append(Paragraph("3. Optional modules (M5, M6)", styles["H2"]))
    flow.append(Paragraph(
        "<b>M5 — Merkle Proof Verifier.</b> For any block the user picks, the "
        "module fetches every txid via "
        "<font face='Courier'>/block/&lt;hash&gt;/txids</font>, converts the "
        "displayed hex strings to internal little-endian byte order, walks the "
        "tree bottom-up duplicating the last hash on odd levels (the "
        "well-known CVE-2012-2459 quirk), and records the sibling hashes along "
        "the path of the chosen transaction. The recomputed root is then "
        "compared against the header's "
        "<font face='Courier'>merkle_root</font>, and the path itself is "
        "re-verified independently in the SPV style — confirming that only "
        "<i>log<sub>2</sub>(n)</i> hashes (32 B each) are needed to prove "
        "inclusion.",
        styles["Body"],
    ))

    flow.append(Paragraph(
        "<b>M6 — Security Score.</b> Two analyses are exposed: (i) the "
        "operating cost per hour to match the network hash rate, computed as "
        "<font face='Courier'>H · J/TH · $/kWh</font> with user-configurable "
        "ASIC efficiency and electricity price, and (ii) the probability that "
        "an attacker holding fraction <i>q</i> of the hash power overtakes the "
        "honest chain after <i>z</i> confirmations, computed with Nakamoto's "
        "§11 formula:",
        styles["Body"],
    ))
    flow.append(Paragraph(
        "P = 1 − Σ<sub>k=0..z</sub> (λ<sup>k</sup> · e<sup>−λ</sup> / k!) · "
        "(1 − (q/p)<sup>z−k</sup>),  λ = z·q/p",
        styles["Mono"],
    ))
    flow.append(Paragraph(
        "The implementation was validated against the table in the original "
        "Bitcoin whitepaper: the canonical reference points (q = 0.10 z = 5; "
        "q = 0.30 z = 5; q = 0.30 z = 10) match to seven decimals. The result "
        "is plotted on a logarithmic axis so the exponential decay against z "
        "is visible immediately — and confirms why the canonical "
        "six-confirmation rule is considered safe for q ≤ 0.10.",
        styles["Body"],
    ))

    # ── section 4: engineering notes ─────────────────────────────────────────
    flow.append(Paragraph("4. Engineering notes", styles["H2"]))
    flow.append(Paragraph(
        "The dashboard is built with Streamlit, plots with Plotly, and refreshes "
        "automatically every 60 s through <font face='Courier'>"
        "st.cache_data(ttl=60)</font> + a "
        "<font face='Courier'>time.sleep + st.rerun()</font> loop. The API "
        "client uses a primary/fallback pattern to survive transient outages of "
        "either provider. The cryptographic helpers — "
        "<font face='Courier'>bits_to_target</font>, "
        "<font face='Courier'>bits_to_difficulty</font>, "
        "<font face='Courier'>sha256d</font> — are reused by every module, "
        "making it straightforward to add further analyses without touching "
        "the network layer.",
        styles["Body"],
    ))

    # ── section 5: references ─────────────────────────────────────────────────
    flow.append(Paragraph("5. References", styles["H2"]))
    refs = [
        "[1] Nakamoto, S. (2008). <i>Bitcoin: A Peer-to-Peer Electronic Cash "
        "System.</i> §6 (Difficulty), §7 (Merkle Trees), §11 (Calculations). "
        "https://bitcoin.org/bitcoin.pdf",
        "[2] mempool.space REST API documentation. "
        "https://mempool.space/docs/api/rest",
        "[3] Blockstream Esplora HTTP API reference. "
        "https://github.com/Blockstream/esplora/blob/master/API.md",
        "[4] Liu, F. T., Ting, K. M., &amp; Zhou, Z.-H. (2008). "
        "<i>Isolation Forest.</i> ICDM 2008. "
        "https://doi.org/10.1109/ICDM.2008.17",
        "[5] scikit-learn user guide — Outlier detection / Isolation Forest. "
        "https://scikit-learn.org/stable/modules/outlier_detection.html",
        "[6] Bitcoin Core developers — block header serialization. "
        "https://developer.bitcoin.org/reference/block_chain.html",
    ]
    ref_style = ParagraphStyle(
        name="Ref", parent=styles["Body"], alignment=TA_LEFT, leading=13,
        spaceAfter=4,
    )
    for r in refs:
        flow.append(Paragraph(r, ref_style))

    flow.append(Spacer(1, 0.2*cm))
    flow.append(Paragraph(
        "All code in this report can be regenerated from the repository: every "
        "metric, every chart, every claim is backed by an inspection step "
        "exposed in the dashboard UI. The PDF itself is built by "
        "<font face='Courier'>report/build_report.py</font>, so the report is "
        "reproducible from source.",
        styles["Caption"],
    ))

    doc.build(flow)
    print(f"Wrote {OUT_PATH}  ({OUT_PATH.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    build()
