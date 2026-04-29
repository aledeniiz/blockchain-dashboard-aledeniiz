"""
modules/m5_merkle.py  —  M5 (optional): Merkle Proof Verifier

Picks any transaction in a block and verifies its Merkle path step by step,
recomputing every double-SHA256 until reaching the block's merkle_root.

Bitcoin Merkle tree rules:
  1. Hashes are SHA256(SHA256(data)) (a.k.a. SHA256d).
  2. txids are stored in *internal byte order* — the API returns them in
     display order (reversed), so we reverse them before hashing.
  3. If a level has an odd number of hashes, the last one is duplicated
     (this is the well-known CVE-2012-2459 quirk).
  4. The final root, reversed to display order, must equal the
     `merkle_root` field in the 80-byte block header.
"""

import hashlib
import requests
import streamlit as st

from api.blockchain_client import BASE_URL


# ── crypto helpers ─────────────────────────────────────────────────────────────

def sha256d(data: bytes) -> bytes:
    """Bitcoin's double SHA-256."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hex_to_internal(h: str) -> bytes:
    """Display-hex (big-endian) -> internal little-endian bytes."""
    return bytes.fromhex(h)[::-1]


def internal_to_hex(b: bytes) -> str:
    """Internal little-endian bytes -> display-hex."""
    return b[::-1].hex()


# ── Merkle path computation ───────────────────────────────────────────────────

def compute_merkle_path(txids_hex: list, target_index: int):
    """
    Walk the Merkle tree bottom-up, recording the sibling hash at each level
    for `target_index`. Returns (root_hex, path, levels) where:
      - root_hex is the recomputed root in display order
      - path is a list of {sibling_hex, position} dicts
      - levels is a list of all intermediate levels (for visualisation)
    """
    level = [hex_to_internal(t) for t in txids_hex]
    levels = [list(level)]
    path = []
    idx = target_index

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate last (Bitcoin quirk)

        sibling_idx = idx ^ 1   # XOR 1 flips the lowest bit -> sibling
        path.append({
            "level":     len(levels) - 1,
            "sibling":   internal_to_hex(level[sibling_idx]),
            "position":  "left"  if sibling_idx < idx else "right",
        })

        new_level = [
            sha256d(level[i] + level[i + 1])
            for i in range(0, len(level), 2)
        ]
        level = new_level
        levels.append(list(level))
        idx //= 2

    return internal_to_hex(level[0]), path, levels


def verify_path(target_txid_hex: str, path: list, expected_root_hex: str) -> bool:
    """
    Independently re-hash the path. We do *not* use compute_merkle_path's root
    here — this function proves the path alone is sufficient, the way a SPV
    light client would verify inclusion.
    """
    h = hex_to_internal(target_txid_hex)
    for step in path:
        sibling = hex_to_internal(step["sibling"])
        h = sha256d(sibling + h) if step["position"] == "left" else sha256d(h + sibling)
    return internal_to_hex(h) == expected_root_hex


# ── data fetch ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_txids(block_hash: str) -> list:
    """Fetch every txid in a block (already in display/big-endian order)."""
    resp = requests.get(f"{BASE_URL}/block/{block_hash}/txids", timeout=30)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=300)
def fetch_block_meta(block_hash: str) -> dict:
    resp = requests.get(f"{BASE_URL}/block/{block_hash}", timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── render ─────────────────────────────────────────────────────────────────────

def render(blocks: list):
    st.markdown("### 🌳 Merkle Proof Verifier")
    st.caption("Recompute the Merkle path of any transaction and check it matches the block header's merkle_root.")

    if not blocks:
        st.warning("No block data available.")
        return

    # ── block picker ───────────────────────────────────────────────────────────
    options = {f"#{b['height']:,}  ·  {b['tx_count']:,} tx": b for b in reversed(blocks[-15:])}
    label = st.selectbox("Block to inspect", list(options.keys()), index=0)
    block = options[label]

    # avoid 10k-tx blocks for the demo
    if block["tx_count"] > 4000:
        st.warning(f"This block has {block['tx_count']:,} txs — Merkle computation is slow but still correct.")

    with st.spinner("Fetching txids and block metadata…"):
        try:
            txids   = fetch_txids(block["id"])
            meta    = fetch_block_meta(block["id"])
        except Exception as e:
            st.error(f"API error: {e}")
            return

    expected_root = meta["merkle_root"]
    n_tx = len(txids)

    # ── tx picker ──────────────────────────────────────────────────────────────
    st.markdown(f"**Block hash:** `{block['id']}`")
    st.markdown(f"**Header `merkle_root`:** `{expected_root}`")
    st.markdown(f"**Transactions in block:** `{n_tx:,}`  ·  tree depth ≈ `{(n_tx - 1).bit_length()}` levels")

    # default to coinbase (index 0) — always present
    max_idx = n_tx - 1
    idx = st.number_input(
        "Transaction index to verify (0 = coinbase)",
        min_value=0, max_value=max_idx,
        value=0, step=1,
    )
    target_txid = txids[idx]
    st.markdown(f"**Target txid:** `{target_txid}`")

    st.divider()

    # ── compute & verify ───────────────────────────────────────────────────────
    with st.spinner("Computing Merkle root and path…"):
        recomputed_root, path, levels = compute_merkle_path(txids, idx)
        path_valid = verify_path(target_txid, path, expected_root)
        root_match = recomputed_root == expected_root

    c1, c2, c3 = st.columns(3)
    c1.metric("Path length (hashes)", f"{len(path)}")
    c2.metric("Bytes transmitted",     f"{32 * len(path)} B")
    c3.metric("vs full block",         f"~{(32 * len(path)) / (block.get('size', 1)) * 100:.4f} %")

    if root_match and path_valid:
        st.success(f"✅  **Merkle root matches** — recomputed root equals header `merkle_root`. "
                   f"Path independently verified with only {len(path)} hashes (SPV-style).")
    else:
        st.error(f"❌ Mismatch. Recomputed: `{recomputed_root}`  ·  expected: `{expected_root}`")

    st.divider()

    # ── step-by-step path ──────────────────────────────────────────────────────
    st.markdown("### 🧮 Merkle Path (step by step)")
    st.caption("Each row hashes the running value with one sibling. `SHA256²` = SHA-256 applied twice.")

    md  = "| Step | Level size | Sibling position | Sibling hash (display order) |\n"
    md += "|------|-----------|------------------|------------------------------|\n"
    for i, step in enumerate(path, 1):
        size = len(levels[step["level"]])
        sib_short = step["sibling"][:24] + "…" + step["sibling"][-8:]
        md += f"| {i} | {size} | **{step['position']}** | `{sib_short}` |\n"
    st.markdown(md)

    # ── reproducible code ──────────────────────────────────────────────────────
    with st.expander("🔬 Reproduce this verification in a Python REPL"):
        # build a small demo with first two path steps
        demo_steps = path[:2] if len(path) >= 2 else path
        demo_lines = []
        for s in demo_steps:
            demo_lines.append(
                f"#  {s['position']:>5} sibling: {s['sibling'][:20]}…\n"
                f"h = sha256d({'sib + h' if s['position']=='left' else 'h + sib'})"
            )
        demo_block = "\n".join(demo_lines)

        st.code(f"""import hashlib

def sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

# txid in *internal* (little-endian) order
target = bytes.fromhex("{target_txid}")[::-1]

h = target
{demo_block}
# ... (continue for all {len(path)} sibling hashes) ...

merkle_root_recomputed = h[::-1].hex()
print(merkle_root_recomputed == "{expected_root}")  # -> {str(root_match)}""",
            language="python",
        )

    # ── theory ─────────────────────────────────────────────────────────────────
    with st.expander("📖 Why Merkle proofs are powerful"):
        st.markdown(f"""
A Merkle proof lets a light client (SPV wallet) confirm that a transaction is
included in a block by downloading **only `log₂(n)` hashes** (32 B each)
instead of the full block.

For this block:
- Full block size: ~`{block.get('size', 0):,}` bytes
- Merkle proof size: `{32 * len(path)}` bytes
- Compression ratio: ~`{block.get('size', 1) / max(32 * len(path), 1):,.0f}×`

The proof is a chain of double-SHA-256 operations. If any sibling along the
path is altered, the recomputed root will not match the header's `merkle_root`,
and the block's PoW would have to be redone — which is computationally
infeasible. This is what makes Merkle trees the backbone of Bitcoin's
inclusion proofs and of every blockchain that followed.
""")
