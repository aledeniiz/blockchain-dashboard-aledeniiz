# CryptoChain Analyzer Dashboard

**Estudiante:** Alejandro Déniz Solana · [@aledeniiz](https://github.com/aledeniiz)  
**Asignatura:** Criptografía y Ciberseguridad — Universidad Alfonso X el Sabio (UAX)  
**Profesor:** Jorge Calvo · [@jmcalvomartin](https://github.com/jmcalvomartin)  
**Curso:** 2025–26

---

## ¿Qué es esto?

Dashboard interactivo en Python/Streamlit que monitoriza métricas criptográficas de Bitcoin en tiempo real, sin necesidad de API key. Construido como práctica de la asignatura de Criptografía.

**API utilizada:** [mempool.space](https://mempool.space/api) (primaria) + [Blockstream](https://blockstream.info/api) (fallback)  
**Auto-refresh:** cada 60 segundos con datos en vivo del bloque más reciente.

---

## Módulos

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| **M1 · Proof of Work** | Dificultad actual, hash rate estimado, distribución de tiempos entre bloques con curva teórica Exp(λ=1/10min) | ✅ Completo |
| **M2 · Block Header** | Parseo del header de 80 bytes (versión, prev_hash, merkle root, timestamp, bits, nonce) + verificación manual SHA256² con `hashlib` | ✅ Completo |
| **M3 · Difficulty History** | Histórico de ajustes de dificultad por época (cada 2016 bloques), ratio tiempo real vs objetivo 600s | ✅ Completo |
| **M4 · AI Anomaly Detector** | Isolation Forest sobre tiempos inter-bloque; detecta bloques estadísticamente anómalos respecto a la distribución Exponencial esperada | ✅ Completo |

---

## IA elegida (M4) — Justificación

**Modelo:** Isolation Forest (`scikit-learn`)

Los tiempos entre bloques de Bitcoin siguen una distribución Exponencial(λ=1/600s) porque el proceso de minado es un proceso de Poisson: cada intento de hash tiene probabilidad de éxito constante e independiente. Desviaciones estadísticas de esta baseline pueden indicar:

- Coordinación entre pools mineros (block withholding)
- Particiones de red o retrasos de propagación
- Eventos de cadena huérfana

Isolation Forest es ideal aquí porque **no requiere datos etiquetados** y aísla anomalías mediante particiones aleatorias — los puntos anómalos (bloques demasiado rápidos o lentos) se aíslan en menos pasos que los bloques normales agrupados en torno a 10 minutos.

**Features usadas:** `log(inter_block_time + 1)` + `tx_count`

---

## Estructura del proyecto

```
blockchain-dashboard-aledeniiz/
├── app.py                      # Entry point: streamlit run app.py
├── requirements.txt
├── api/
│   └── blockchain_client.py    # Cliente API: get_blocks, bits_to_difficulty, etc.
└── modules/
    ├── m1_pow.py               # M1 · Proof of Work Monitor
    ├── m2_header.py            # M2 · Block Header Analyzer
    ├── m3_difficulty.py        # M3 · Difficulty History
    └── m4_ai.py                # M4 · AI Anomaly Detector
```

---

## Cómo ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Arrancar el dashboard
streamlit run app.py
```

Abre http://localhost:8501 en tu navegador.

---

## Conceptos criptográficos clave

- **Proof of Work:** SHA256(SHA256(header_bytes)) < target. El minero itera el nonce hasta encontrar un hash con suficientes ceros iniciales.
- **Campo `bits`:** codificación compacta (nBits) del target de 256 bits. `bits = 0xAABBCCDD → T = 0x00BBCCDD × 256^(AA−3)`
- **Dificultad:** `genesis_target / T`, se reajusta cada 2016 bloques (~2 semanas) para mantener ~10 min/bloque.
- **Header de 80 bytes:** `version (4B) | prev_hash (32B) | merkle_root (32B) | timestamp (4B) | bits (4B) | nonce (4B)` — en little-endian.
