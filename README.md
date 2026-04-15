# CryptoChain Analyzer Dashboard

**Student:** Alejandro Déniz Solana  
**GitHub:** aledeniiz  
**Course:** Cryptography — Universidad Alfonso X el Sabio  
**Professor:** Jorge Calvo (jmcalvomartin)  
**Academic Year:** 2025–26

---

## Project Title
CryptoChain Analyzer Dashboard — Live Bitcoin Cryptographic Metrics + AI Anomaly Detector

## Chosen AI Approach (M4)
**Anomaly Detector** — Identifies blocks whose inter-arrival time is statistically abnormal.  
Block times follow an exponential distribution (memoryless Poisson process). Deviations from this baseline may indicate mining pool coordination or network events.  
Model: Isolation Forest trained on real inter-block time data from Blockstream API.  
Evaluation metric: contamination rate, anomaly score distribution, comparison vs. exponential baseline.

## How to Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Module Status

| Module | Description | Status |
|--------|-------------|--------|
| M1 | Proof of Work Monitor (difficulty, block times, hash rate) | 🟡 In progress |
| M2 | Block Header Analyzer + SHA256 manual PoW verification | 🟡 In progress |
| M3 | Difficulty History (last adjustment periods, ratio actual/target) | 🟡 In progress |
| M4 | AI Anomaly Detector (inter-block time, Isolation Forest) | 🟡 In progress |

## Current Progress
- Repository created and connected to GitHub
- Project structure set up (api/, modules/, report/)
- First API call to Blockstream working (latest block data)
- Blockstream endpoints explored and documented

## Next Step
Implement M1 dashboard panel with live difficulty and block time histogram.

## Main Problem or Blocker
None currently.
