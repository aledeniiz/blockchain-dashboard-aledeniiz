# CryptoChain Analyzer Dashboard

**Student:** Alejandro Déniz Solana · [@aledeniiz](https://github.com/aledeniiz)
**Course:** Cryptography and Cybersecurity — Universidad Alfonso X el Sabio (UAX)
**Instructor:** Jorge Calvo · [@jmcalvomartin](https://github.com/jmcalvomartin)
**Academic year:** 2025–26

---

## What is this?

Interactive Python/Streamlit dashboard that monitors Bitcoin cryptographic
metrics in real time, with no API key required. Built as the individual
project for the Cryptography course (Topic 7 — Hash Functions and Blockchain).

**APIs used:** [mempool.space](https://mempool.space/api) (primary) +
[Blockstream](https://blockstream.info/api) (fallback)
**Auto-refresh:** every 60 seconds with live data from the latest block.

---

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| **M1 · Proof of Work** | Current difficulty, estimated network hash rate, inter-block time histogram with theoretical Exp(λ = 1/10 min) overlay | ✅ Done |
| **M2 · Block Header** | 80-byte header parse (version, prev_hash, merkle_root, timestamp, bits, nonce) + manual `SHA256²` verification with `hashlib` | ✅ Done |
| **M3 · Difficulty History** | Per-epoch difficulty adjustment history (every 2016 blocks), ratio of actual time vs the 600 s target | ✅ Done |
| **M4 · AI Anomaly Detector** | Isolation Forest on inter-block times, flags blocks deviating from the expected exponential baseline | ✅ Done |
| **M5 · Merkle Proof Verifier** *(optional)* | Pick a transaction, recompute the Merkle path step by step, verify it equals the header's `merkle_root` | ✅ Done |
| **M6 · Security Score** *(optional)* | USD/hour cost of a 51 % attack from live hash rate; Nakamoto §11 confirmation-depth attack probability | ✅ Done |

---

## Chosen AI approach (M4) — Justification

**Model:** Isolation Forest (`scikit-learn`)

Bitcoin inter-block times follow an Exponential(λ = 1/600 s) distribution because
mining is a memoryless Poisson process: every hash attempt has constant,
independent success probability. Statistical deviations from this baseline can
indicate:

- Coordination between mining pools (block withholding)
- Network partitions or propagation delays
- Stale / orphan-chain events

Isolation Forest is a good fit here because **no labeled data is required** and
it isolates anomalies through random partitioning — anomalous points
(unusually fast or slow blocks) are isolated in fewer splits than the bulk of
the data clustered around 10 minutes.

**Features used:** `log(inter_block_time + 1)` + `tx_count`
**Evaluation:** percentage of blocks flagged at the chosen contamination rate,
plus visual inspection against the theoretical Exp(λ = 1/600 s) curve.

---

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
    └── report.pdf              # Final 2-3 page report
```

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the dashboard
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

---

## Key cryptographic concepts

- **Proof of Work:** `SHA256(SHA256(header_bytes)) < target`. The miner iterates
  the nonce until it finds a hash with enough leading zeros.
- **`bits` field:** compact (nBits) encoding of the 256-bit target.
  `bits = 0xAABBCCDD → T = 0x00BBCCDD × 256^(0xAA − 3)`.
- **Difficulty:** `genesis_target / T`, retargeted every 2016 blocks (~2 weeks)
  to keep the network at ~10 min/block.
- **80-byte header:** `version (4B) | prev_hash (32B) | merkle_root (32B) |
  timestamp (4B) | bits (4B) | nonce (4B)` — little-endian.
- **Merkle tree:** all transactions in a block are paired and hashed
  (`SHA256²`) up the tree until a single root is produced. A Merkle proof
  needs only `log₂(n)` hashes to verify a transaction is included.

---

## Project tracking

- **Current progress:** M1–M4 implemented and verified live on mainnet.
  Optional M5 (Merkle proof verifier) and M6 (51 % attack cost + Nakamoto §11
  attack probability) implemented. M6 verified against the original whitepaper
  Table 1 (q=0.10 z=5, q=0.30 z=5, q=0.30 z=10 match to 7 decimals).
- **Next step:** add the final PDF report under `report/`, then run the
  in-class checkpoint demo with auto-refresh active.
- **Main blocker:** none at the moment — the dashboard runs end-to-end against
  live mempool.space data.

## References

- Nakamoto, S. (2008). [*Bitcoin: A Peer-to-Peer Electronic Cash System*](https://bitcoin.org/bitcoin.pdf), §6 (Difficulty), §7 (Merkle Trees), §11 (Calculations).
- mempool.space REST API documentation — <https://mempool.space/docs/api/rest>
- Blockstream Esplora API documentation — <https://github.com/Blockstream/esplora/blob/master/API.md>
- scikit-learn Isolation Forest user guide — <https://scikit-learn.org/stable/modules/outlier_detection.html#isolation-forest>

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-16 09:59 CEST
Status: Amber

Strength:
- Your repository keeps the expected classroom structure.

Improve now:
- The README is present but still misses part of the required kickoff information.

Next step:
- Complete the README fields for student information, AI approach, module status, and next step.
<!-- student-repo-auditor:teacher-feedback:end -->
