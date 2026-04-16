# CryptoChain Analyzer Dashboard

**Estudiante:** Alejandro DÃ©niz Solana Â· [@aledeniiz](https://github.com/aledeniiz)  
**Asignatura:** CriptografÃ­a y Ciberseguridad â€” Universidad Alfonso X el Sabio (UAX)  
**Profesor:** Jorge Calvo Â· [@jmcalvomartin](https://github.com/jmcalvomartin)  
**Curso:** 2025â€“26

---

## Â¿QuÃ© es esto?

Dashboard interactivo en Python/Streamlit que monitoriza mÃ©tricas criptogrÃ¡ficas de Bitcoin en tiempo real, sin necesidad de API key. Construido como prÃ¡ctica de la asignatura de CriptografÃ­a.

**API utilizada:** [mempool.space](https://mempool.space/api) (primaria) + [Blockstream](https://blockstream.info/api) (fallback)  
**Auto-refresh:** cada 60 segundos con datos en vivo del bloque mÃ¡s reciente.

---

## MÃ³dulos

| MÃ³dulo | DescripciÃ³n | Estado |
|--------|-------------|--------|
| **M1 Â· Proof of Work** | Dificultad actual, hash rate estimado, distribuciÃ³n de tiempos entre bloques con curva teÃ³rica Exp(Î»=1/10min) | âœ… Completo |
| **M2 Â· Block Header** | Parseo del header de 80 bytes (versiÃ³n, prev_hash, merkle root, timestamp, bits, nonce) + verificaciÃ³n manual SHA256Â² con `hashlib` | âœ… Completo |
| **M3 Â· Difficulty History** | HistÃ³rico de ajustes de dificultad por Ã©poca (cada 2016 bloques), ratio tiempo real vs objetivo 600s | âœ… Completo |
| **M4 Â· AI Anomaly Detector** | Isolation Forest sobre tiempos inter-bloque; detecta bloques estadÃ­sticamente anÃ³malos respecto a la distribuciÃ³n Exponencial esperada | âœ… Completo |

---

## IA elegida (M4) â€” JustificaciÃ³n

**Modelo:** Isolation Forest (`scikit-learn`)

Los tiempos entre bloques de Bitcoin siguen una distribuciÃ³n Exponencial(Î»=1/600s) porque el proceso de minado es un proceso de Poisson: cada intento de hash tiene probabilidad de Ã©xito constante e independiente. Desviaciones estadÃ­sticas de esta baseline pueden indicar:

- CoordinaciÃ³n entre pools mineros (block withholding)
- Particiones de red o retrasos de propagaciÃ³n
- Eventos de cadena huÃ©rfana

Isolation Forest es ideal aquÃ­ porque **no requiere datos etiquetados** y aÃ­sla anomalÃ­as mediante particiones aleatorias â€” los puntos anÃ³malos (bloques demasiado rÃ¡pidos o lentos) se aÃ­slan en menos pasos que los bloques normales agrupados en torno a 10 minutos.

**Features usadas:** `log(inter_block_time + 1)` + `tx_count`

---

## Estructura del proyecto

```
blockchain-dashboard-aledeniiz/
â”œâ”€â”€ app.py                      # Entry point: streamlit run app.py
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ api/
â”‚   â””â”€â”€ blockchain_client.py    # Cliente API: get_blocks, bits_to_difficulty, etc.
â””â”€â”€ modules/
    â”œâ”€â”€ m1_pow.py               # M1 Â· Proof of Work Monitor
    â”œâ”€â”€ m2_header.py            # M2 Â· Block Header Analyzer
    â”œâ”€â”€ m3_difficulty.py        # M3 Â· Difficulty History
    â””â”€â”€ m4_ai.py                # M4 Â· AI Anomaly Detector
```

---

## CÃ³mo ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Arrancar el dashboard
streamlit run app.py
```

Abre http://localhost:8501 en tu navegador.

---

## Conceptos criptogrÃ¡ficos clave

- **Proof of Work:** SHA256(SHA256(header_bytes)) < target. El minero itera el nonce hasta encontrar un hash con suficientes ceros iniciales.
- **Campo `bits`:** codificaciÃ³n compacta (nBits) del target de 256 bits. `bits = 0xAABBCCDD â†’ T = 0x00BBCCDD Ã— 256^(AAâˆ’3)`
- **Dificultad:** `genesis_target / T`, se reajusta cada 2016 bloques (~2 semanas) para mantener ~10 min/bloque.
- **Header de 80 bytes:** `version (4B) | prev_hash (32B) | merkle_root (32B) | timestamp (4B) | bits (4B) | nonce (4B)` â€” en little-endian.

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
