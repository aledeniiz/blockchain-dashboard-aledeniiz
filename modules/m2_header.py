"""
modules/m2_header.py  —  M2: Block Header Analyzer
80-byte header + manual SHA256² Proof-of-Work verification.
"""

import hashlib
import struct
import requests
import streamlit as st

from api.blockchain_client import BASE_URL, bits_to_target, bits_to_difficulty


# ── helpers ────────────────────────────────────────────────────────────────────

def fetch_block_header_raw(block_hash: str) -> bytes:
    resp = requests.get(f"{BASE_URL}/block/{block_hash}/header", timeout=15)
    resp.raise_for_status()
    return bytes.fromhex(resp.text.strip())


def parse_header(raw: bytes) -> dict:
    assert len(raw) == 80
    return {
        "version":     struct.unpack_from("<I", raw,  0)[0],
        "prev_hash":   raw[ 4:36][::-1].hex(),
        "merkle_root": raw[36:68][::-1].hex(),
        "timestamp":   struct.unpack_from("<I", raw, 68)[0],
        "bits":        struct.unpack_from("<I", raw, 72)[0],
        "nonce":       struct.unpack_from("<I", raw, 76)[0],
    }


def verify_pow(raw: bytes) -> dict:
    h1 = hashlib.sha256(raw).digest()
    h2 = hashlib.sha256(h1).digest()
    display = h2[::-1].hex()
    hash_int = int(display, 16)
    bits     = struct.unpack_from("<I", raw, 72)[0]
    target   = bits_to_target(bits)
    lz       = 256 - hash_int.bit_length() if hash_int else 256
    return {
        "hash":       display,
        "hash_int":   hash_int,
        "target":     target,
        "target_hex": hex(target),
        "difficulty": bits_to_difficulty(bits),
        "valid":      hash_int < target,
        "lz_bits":    lz,
    }


# ── render ─────────────────────────────────────────────────────────────────────

def render(blocks: list):
    if not blocks:
        st.warning("No block data available.")
        return

    latest     = blocks[-1]
    block_hash = latest["id"]

    # ── block selector ─────────────────────────────────────────────────────────
    st.markdown("### 🔍 Select Block")
    options = {f"#{b['height']:,}  —  {b['id'][:20]}…": b for b in reversed(blocks[-20:])}
    chosen_label = st.selectbox("Block to inspect", list(options.keys()), index=0)
    chosen_block = options[chosen_label]
    block_hash   = chosen_block["id"]

    st.markdown(
        f"**Hash:** `{block_hash}`  ·  **Height:** `{chosen_block['height']:,}`",
    )

    with st.spinner("Fetching raw 80-byte header…"):
        try:
            raw    = fetch_block_header_raw(block_hash)
            fields = parse_header(raw)
            result = verify_pow(raw)
        except Exception as e:
            st.error(f"Could not fetch header: {e}")
            return

    st.divider()

    # ── header structure ───────────────────────────────────────────────────────
    st.markdown("### 🗂️ 80-byte Header Structure")
    st.caption("Serialized in little-endian. Prev-hash and Merkle-root are displayed reversed (Bitcoin display convention).")

    left, right = st.columns([1, 1])

    with left:
        FIELDS = [
            ("Version",     "0 – 3",   f"`{fields['version']}`"),
            ("Prev Hash",   "4 – 35",  f"`{fields['prev_hash'][:28]}…`"),
            ("Merkle Root", "36 – 67", f"`{fields['merkle_root'][:28]}…`"),
            ("Timestamp",   "68 – 71", f"`{fields['timestamp']}` (Unix)"),
            ("Bits",        "72 – 75", f"`{hex(fields['bits'])}`"),
            ("Nonce",       "76 – 79", f"`{fields['nonce']:,}`"),
        ]
        header_md  = "| Field | Bytes | Value |\n"
        header_md += "|-------|-------|-------|\n"
        for name, byterange, value in FIELDS:
            header_md += f"| **{name}** | {byterange} | {value} |\n"
        st.markdown(header_md)

    with right:
        st.markdown("**Raw header (160 hex chars = 80 bytes):**")
        # Split into 4 lines of 40 chars for readability
        raw_hex = raw.hex()
        formatted = "\n".join(
            f"[{i*10:02d}–{i*10+9:02d}B]  {raw_hex[i*20:i*20+20]}"
            for i in range(8)
        )
        st.code(formatted, language="text")

    st.divider()

    # ── PoW verification ───────────────────────────────────────────────────────
    st.markdown("### 🔐 Manual Proof-of-Work Verification")
    st.caption("Computed with Python's `hashlib` — no external library needed.")

    st.code(f"""import hashlib, struct

header_bytes = bytes.fromhex("{raw.hex()[:40]}…")  # 80 bytes

# Step 1: double SHA-256
h1 = hashlib.sha256(header_bytes).digest()
h2 = hashlib.sha256(h1).digest()

# Step 2: reverse byte order for display (Bitcoin convention)
display_hash = h2[::-1].hex()
# → {result['hash']}

# Step 3: decode target from bits field
bits        = struct.unpack_from("<I", header_bytes, 72)[0]  # {hex(fields['bits'])}
exponent    = bits >> 24                 # {fields['bits'] >> 24}
coefficient = bits & 0x007FFFFF         # {hex(fields['bits'] & 0x007FFFFF)}
target      = coefficient * 256 ** (exponent - 3)
# → {result['target_hex']}

# Step 4: verify hash < target
print(int(display_hash, 16) < target)   # {result['valid']}""",
        language="python",
    )

    # ── result banner ──────────────────────────────────────────────────────────
    if result["valid"]:
        st.success("✅  **Proof of Work VALID** — SHA256²(header) < target")
    else:
        st.error("❌  Proof of Work INVALID")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leading Zero Bits", f"{result['lz_bits']}")
    c2.metric("Difficulty",        f"{result['difficulty']/1e12:.2f} T")
    c3.metric("Nonce",             f"{fields['nonce']:,}")
    c4.metric("Header Size",       "80 bytes")

    st.divider()

    # ── bits explainer ─────────────────────────────────────────────────────────
    with st.expander("📖 How the `bits` field encodes the target"):
        exp  = fields['bits'] >> 24
        coef = fields['bits'] & 0x007FFFFF
        st.markdown(f"""
`bits = {hex(fields['bits'])}`  breaks down as:

| Part | Value | Role |
|------|-------|------|
| Exponent  | `{exp}` (0x{exp:02x}) | Scale factor: T = coeff × 256^(exp − 3) |
| Coefficient | `{hex(coef)}` | Mantissa of the target |

**Full target:**
```
{result['target_hex']}
```
A valid hash must be numerically **less than** this value,
which is equivalent to having at least **{result['lz_bits']} leading zero bits**.
        """)
