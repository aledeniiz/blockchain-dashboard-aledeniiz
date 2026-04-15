"""
modules/m2_header.py
M2 — Block Header Analyzer

The Bitcoin block header is exactly 80 bytes, serialized in little-endian:
  Bytes  0-3  : version        (4 bytes, little-endian int32)
  Bytes  4-35 : prev_hash      (32 bytes, reversed)
  Bytes 36-67 : merkle_root    (32 bytes, reversed)
  Bytes 68-71 : timestamp      (4 bytes, little-endian uint32)
  Bytes 72-75 : bits           (4 bytes, little-endian uint32)
  Bytes 76-79 : nonce          (4 bytes, little-endian uint32)

Proof of Work verification:
  1. Serialize the header in little-endian as shown above.
  2. Compute H = SHA256(SHA256(header_bytes)).
  3. Interpret H as a 256-bit big-endian integer.
  4. Verify H < target (decoded from bits).

IMPORTANT — byte order:
  Bitcoin hashes are displayed in reversed byte order (big-endian display of a
  little-endian value). When serializing the header, prev_hash and merkle_root
  must be reversed back to little-endian.
"""

import hashlib
import struct
import requests
import streamlit as st

from api.blockchain_client import BASE_URL, bits_to_target, bits_to_difficulty


def fetch_block_header_raw(block_hash: str) -> bytes:
    """
    Fetch the raw 80-byte block header from Blockstream.
    Returns bytes.
    """
    url = f"{BASE_URL}/block/{block_hash}/header"
    resp = requests.get(url, timeout=10)
    # Blockstream returns the header as a hex string
    return bytes.fromhex(resp.text.strip())


def parse_header(header_bytes: bytes) -> dict:
    """
    Parse the 80-byte block header into its 6 fields.
    All multi-byte integers are stored in little-endian in the serialization.
    """
    assert len(header_bytes) == 80, f"Header must be 80 bytes, got {len(header_bytes)}"
    version = struct.unpack_from("<I", header_bytes, 0)[0]
    prev_hash = header_bytes[4:36][::-1].hex()     # reverse to display as big-endian
    merkle_root = header_bytes[36:68][::-1].hex()  # reverse to display as big-endian
    timestamp = struct.unpack_from("<I", header_bytes, 68)[0]
    bits = struct.unpack_from("<I", header_bytes, 72)[0]
    nonce = struct.unpack_from("<I", header_bytes, 76)[0]
    return {
        "version": version,
        "prev_hash": prev_hash,
        "merkle_root": merkle_root,
        "timestamp": timestamp,
        "bits": bits,
        "nonce": nonce,
    }


def verify_proof_of_work(header_bytes: bytes) -> dict:
    """
    Manually verify Proof of Work using Python's hashlib.
    Steps:
      1. Compute H = SHA256(SHA256(header_bytes))
      2. Reverse bytes of H to get display hash (Bitcoin convention)
      3. Decode target from bits field
      4. Check H_int < target
    Returns verification details.
    """
    # Double SHA256
    h1 = hashlib.sha256(header_bytes).digest()
    h2 = hashlib.sha256(h1).digest()

    # Display hash: reverse byte order
    display_hash = h2[::-1].hex()
    hash_int = int(display_hash, 16)

    # Count leading zero bits
    leading_zero_bits = 256 - hash_int.bit_length() if hash_int > 0 else 256

    # Decode target
    bits = struct.unpack_from("<I", header_bytes, 72)[0]
    target = bits_to_target(bits)
    difficulty = bits_to_difficulty(bits)

    valid = hash_int < target

    return {
        "hash": display_hash,
        "hash_int": hash_int,
        "target": target,
        "target_hex": hex(target),
        "difficulty": difficulty,
        "valid": valid,
        "leading_zero_bits": leading_zero_bits,
    }


def render(blocks: list):
    """Render M2 panel in Streamlit."""
    st.subheader("M2 · Block Header Analyzer")

    if not blocks:
        st.warning("No block data available.")
        return

    latest = blocks[-1]
    block_hash = latest["id"]

    st.markdown(f"**Analyzing block:** `{block_hash}`  (height {latest['height']})")

    with st.spinner("Fetching raw 80-byte header..."):
        try:
            header_bytes = fetch_block_header_raw(block_hash)
        except Exception as e:
            st.error(f"Could not fetch raw header: {e}")
            return

    # Parse header fields
    fields = parse_header(header_bytes)

    st.markdown("#### 80-byte Header Structure")
    st.markdown("The Bitcoin block header is **exactly 80 bytes**, serialized in little-endian:")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("| Field | Bytes | Value |")
        st.markdown("|-------|-------|-------|")
        st.markdown(f"| Version | 0–3 | `{fields['version']}` |")
        st.markdown(f"| Prev hash | 4–35 | `{fields['prev_hash'][:20]}...` |")
        st.markdown(f"| Merkle root | 36–67 | `{fields['merkle_root'][:20]}...` |")
        st.markdown(f"| Timestamp | 68–71 | `{fields['timestamp']}` |")
        st.markdown(f"| Bits | 72–75 | `{hex(fields['bits'])}` |")
        st.markdown(f"| Nonce | 76–79 | `{fields['nonce']}` |")

    with col2:
        st.markdown("**Raw header (hex):**")
        st.code(header_bytes.hex(), language="text")

    # Proof of Work verification
    st.markdown("#### Manual Proof of Work Verification")
    st.markdown(
        "Using Python's `hashlib`, we compute `SHA256(SHA256(header_bytes))` "
        "and verify the result is below the target encoded in `bits`."
    )

    result = verify_proof_of_work(header_bytes)

    st.code(
        f"""import hashlib

header_bytes = bytes.fromhex("{header_bytes.hex()[:32]}...") # 80 bytes

h1 = hashlib.sha256(header_bytes).digest()
h2 = hashlib.sha256(h1).digest()
display_hash = h2[::-1].hex()  # reverse byte order (Bitcoin convention)

# Result:
# {result['hash']}

# Target (from bits={hex(fields['bits'])}):
# {result['target_hex']}

# Is hash < target? {result['valid']}""",
        language="python",
    )

    if result["valid"]:
        st.success(f"✅ Proof of Work VALID — hash < target")
    else:
        st.error(f"❌ Proof of Work INVALID")

    col1, col2, col3 = st.columns(3)
    col1.metric("Leading zero bits", result["leading_zero_bits"])
    col2.metric("Difficulty", f"{result['difficulty']/1e12:.2f} T")
    col3.metric("Nonce", f"{fields['nonce']:,}")

    with st.expander("About the bits field"):
        st.markdown(
            f"""
            The `bits` field `{hex(fields['bits'])}` is a compact encoding of the target threshold T:
            - Exponent = `{fields['bits'] >> 24}` (most significant byte)
            - Coefficient = `{hex(fields['bits'] & 0x007FFFFF)}` (lower 3 bytes)
            - T = coefficient × 256^(exponent − 3)
            - Result: `{result['target_hex']}`

            A valid block hash must be numerically **less than** T.
            This means the hash must start with at least **{result['leading_zero_bits']} leading zero bits**.
            """
        )
