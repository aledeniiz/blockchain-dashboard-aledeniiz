# CryptoChain Analyzer Dashboard

## Student Information

- **Name:** Alejandro Déniz Solana
- **GitHub username:** [@aledeniiz](https://github.com/aledeniiz)
- **Course:** Cryptography and Cybersecurity — Universidad Alfonso X el Sabio (UAX)
- **Instructor:** Jorge Calvo · [@jmcalvomartin](https://github.com/jmcalvomartin)
- **Academic year:** 2025–26

## Project Title

CryptoChain Analyzer Dashboard — real-time Bitcoin cryptographic metrics with an AI anomaly detector.

## Chosen AI Approach

**M4 · Anomaly detector — Isolation Forest (`scikit-learn`).**

Bitcoin inter-block times follow an Exponential(λ = 1/600 s) distribution because mining is a memoryless Poisson process. Isolation Forest is unsupervised (no labels needed), scales linearly, and isolates outliers in fewer random splits than inliers — a natural fit for an exponential-tail anomaly problem. Features used: `log(inter_block_time + 1)` and `tx_count`.

## Module Tracking

| Module | Description | Status |
|--------|-------------|--------|
| **M1 · Proof of Work** | Current difficulty, estimated network hash rate, inter-block time histogram with theoretical Exp(λ = 1/10 min) overlay | ✅ Done |
| **M2 · Block Header** | 80-byte header parse (version, prev_hash, merkle_root, timestamp, bits, nonce) + manual `SHA256²` verification with `hashlib` | ✅ Done |
| **M3 · Difficulty History** | Per-epoch difficulty adjustment history (every 2 016 blocks), ratio of actual time vs the 600 s target | ✅ Done |
| **M4 · AI Anomaly Detector** | Isolation Forest on inter-block times, flags blocks deviating from the expected exponential baseline | ✅ Done |
| **M5 · Merkle Proof Verifier** *(optional)* | Pick a transaction, recompute the Merkle path step by step, verify it equals the header's `merkle_root` | ✅ Done |
| **M6 · Security Score** *(optional)* | USD/hour cost of a 51 % attack from live hash rate; Nakamoto §11 confirmation-depth attack probability | ✅ Done |

## Current Progress

- **M1–M4 (required core):** implemented and verified live on Bitcoin mainnet through the mempool.space API (with Blockstream as fallback). Auto-refresh every 60 s.
- **M2 manual PoW check:** the dashboard fetches the raw 80-byte header and reproduces the block hash byte-for-byte using only Python's `hashlib`, confirming `SHA256²(header) < target`.
- **M4 evaluation:** the empirical inter-block histogram is overlaid with the theoretical Exp(λ = 1/600 s) PDF; the model flags the expected fraction of tail events at the chosen contamination rate.
- **Optional M5 and M6:** added for higher rubric coverage. M6's Nakamoto §11 implementation matches the whitepaper Table 1 to 7 decimals on the canonical reference points (q = 0.10 z = 5; q = 0.30 z = 5; q = 0.30 z = 10).
- **Final report:** 2-page PDF committed to `report/report.pdf`, regenerable via `python report/build_report.py`.
- **UI polish:** light theme with Inter typography, glass-morphism hero card, live/stale indicator, and Plotly white templates throughout.

## Next Step

Run the in-class checkpoint demo (29 April) with auto-refresh active to show all six tabs (M1–M6) updating live, then start a small commit cadence over the next two weeks (caption tweaks, screenshot for the README) to keep the commit history honest before the 14 May deadline.

## Main Problem or Blocker

None at the moment — the dashboard runs end-to-end against live mempool.space data with the Blockstream fallback wired up. The only known minor caveat is that very large blocks (>4 000 transactions) make the M5 Merkle recomputation slower in the browser; this is documented inside the M5 module.

---

## What is this?

Interactive Python/Streamlit dashboard that monitors Bitcoin cryptographic metrics in real time, with no API key required. Built as the individual project for the Cryptography course (Topic 7 — Hash Functions and Blockchain).

**APIs used:** [mempool.space](https://mempool.space/api) (primary) + [Blockstream](https://blockstream.info/api) (fallback)
**Auto-refresh:** every 60 seconds with live data from the latest block.

## Project structure

```
blockchain-dashboard-aledeniiz/
├── app.py                      # Entry point: streamlit run app.py
├── requirements.txt
├── api/
│   └── blockchain_client.py    # API client: get_blocks, bits_to_difficulty, ...
├── modules/
│   ├── m1_pow.py               # M1 · Proof of Work Monitor
│   ├── m2_header.py            # M2 · Block Header Analyzer
│   ├── m3_difficulty.py        # M3 · Difficulty History
│   ├── m4_ai.py                # M4 · AI Anomaly Detector
│   ├── m5_merkle.py            # M5 · Merkle Proof Verifier (optional)
│   └── m6_security.py          # M6 · Security Score (optional)
└── report/
    ├── build_report.py         # Reproducible PDF generator (reportlab)
    └── report.pdf              # Final 2-page report
```

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the dashboard
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

## Key cryptographic concepts

- **Proof of Work:** `SHA256(SHA256(header_bytes)) < target`. The miner iterates the nonce until it finds a hash with enough leading zeros.
- **`bits` field:** compact (nBits) encoding of the 256-bit target. `bits = 0xAABBCCDD → T = 0x00BBCCDD × 256^(0xAA − 3)`.
- **Difficulty:** `genesis_target / T`, retargeted every 2 016 blocks (~2 weeks) to keep the network at ~10 min/block.
- **80-byte header:** `version (4B) | prev_hash (32B) | merkle_root (32B) | timestamp (4B) | bits (4B) | nonce (4B)` — little-endian.
- **Merkle tree:** all transactions in a block are paired and hashed (`SHA256²`) up the tree until a single root is produced. A Merkle proof needs only `log₂(n)` hashes to verify a transaction is included.

## References

- Nakamoto, S. (2008). [*Bitcoin: A Peer-to-Peer Electronic Cash System*](https://bitcoin.org/bitcoin.pdf), §6 (Difficulty), §7 (Merkle Trees), §11 (Calculations).
- mempool.space REST API documentation — <https://mempool.space/docs/api/rest>
- Blockstream Esplora API documentation — <https://github.com/Blockstream/esplora/blob/master/API.md>
- scikit-learn Isolation Forest user guide — <https://scikit-learn.org/stable/modules/outlier_detection.html#isolation-forest>
- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). *Isolation Forest.* ICDM 2008. <https://doi.org/10.1109/ICDM.2008.17>

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-29 20:44 CEST
Status: Red

Strength:
- I can see the dashboard structure integrating the checkpoint modules.

Improve now:
- The README should now reflect the checkpoint more explicitly, including progress, blockers, and updated module status.

Next step:
- Update the README so progress, blockers, module status, and next step match the checkpoint format exactly.
<!-- student-repo-auditor:teacher-feedback:end -->
