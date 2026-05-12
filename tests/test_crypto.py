"""
tests/test_crypto.py

Pytest suite for the cryptographic primitives. These tests demonstrate that
every value the dashboard displays is recomputed from scratch — not trusted
from the API. Run with:

    pytest tests/ -v

The tests are split into:
  - Pure-math tests        (offline, deterministic, run on every push)
  - Live-network tests     (mark `live`, skipped if mempool.space is down)
"""

import hashlib
import math
import struct
import sys
from pathlib import Path

import pytest
import requests

# Make 'api' and 'modules' importable when running pytest from the repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.blockchain_client import (         # noqa: E402
    BASE_URL, bits_to_target, bits_to_difficulty,
    get_latest_block, get_raw_header,
)
from modules.m5_merkle import (             # noqa: E402
    sha256d, hex_to_internal, internal_to_hex,
    compute_merkle_path, verify_path,
)
from modules.m6_security import (           # noqa: E402
    attack_success_probability,
)


# ───────────────────────────────────────────────────────────────────────────────
# 1. bits → target → difficulty
# ───────────────────────────────────────────────────────────────────────────────

class TestBitsTarget:
    """The `bits` field is the compact encoding of the 256-bit PoW target."""

    def test_genesis_bits_decodes_to_genesis_target(self):
        # Bitcoin genesis: bits = 0x1d00ffff → target = 0x00000000FFFF...
        target = bits_to_target(0x1d00ffff)
        expected = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        assert target == expected

    def test_difficulty_at_genesis_is_one(self):
        # By definition difficulty = genesis_target / current_target → 1.0 at genesis
        assert bits_to_difficulty(0x1d00ffff) == pytest.approx(1.0, rel=1e-12)

    def test_target_decreases_as_difficulty_increases(self):
        # A "harder" bits value (smaller mantissa or smaller exponent) → lower target
        easy = bits_to_target(0x1d00ffff)            # genesis
        hard = bits_to_target(0x17000123)            # contemporary mainnet
        assert hard < easy
        # And difficulty must be > 1 by many orders of magnitude
        assert bits_to_difficulty(0x17000123) > 1e10

    def test_bits_hex_string_and_int_give_same_result(self):
        assert bits_to_target("0x1d00ffff") == bits_to_target(0x1d00ffff)


# ───────────────────────────────────────────────────────────────────────────────
# 2. Double-SHA256 helpers
# ───────────────────────────────────────────────────────────────────────────────

class TestSha256d:
    """Bitcoin uses SHA256(SHA256(x))."""

    def test_empty_input(self):
        # Known SHA256d("") = 5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456
        digest = sha256d(b"")
        assert digest.hex() == "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456"

    def test_matches_manual_double_sha(self):
        # Property: sha256d(x) == sha256(sha256(x))
        data = b"hello bitcoin"
        manual = hashlib.sha256(hashlib.sha256(data).digest()).digest()
        assert sha256d(data) == manual

    def test_byte_order_helpers_round_trip(self):
        h = "aa" * 32
        assert internal_to_hex(hex_to_internal(h)) == h


# ───────────────────────────────────────────────────────────────────────────────
# 3. Merkle math
# ───────────────────────────────────────────────────────────────────────────────

class TestMerkle:
    """Bottom-up SHA256d tree, with the CVE-2012-2459 odd-duplication quirk."""

    def test_single_txid_returns_itself(self):
        txid = "aa" * 32
        root, path, _ = compute_merkle_path([txid], 0)
        assert root == txid
        assert path == []

    def test_two_txids_combine(self):
        a, b = "01" * 32, "02" * 32
        # Expected manual: sha256d(internal(a) + internal(b)) reversed
        expected = internal_to_hex(sha256d(hex_to_internal(a) + hex_to_internal(b)))
        root, path, _ = compute_merkle_path([a, b], 0)
        assert root == expected
        assert len(path) == 1
        assert path[0]["position"] == "right"
        assert verify_path(a, path, expected)

    def test_three_txids_odd_duplication(self):
        # CVE-2012-2459 quirk: last hash is duplicated on odd levels
        a, b, c = "01"*32, "02"*32, "03"*32
        h_ab = sha256d(hex_to_internal(a) + hex_to_internal(b))
        h_cc = sha256d(hex_to_internal(c) + hex_to_internal(c))  # duplicate
        expected = internal_to_hex(sha256d(h_ab + h_cc))
        root, path, _ = compute_merkle_path([a, b, c], 2)
        assert root == expected
        assert verify_path(c, path, expected)

    def test_four_txids_balanced(self):
        ids = [f"{i:02x}"*32 for i in range(1, 5)]
        # Recompute root manually
        level = [hex_to_internal(t) for t in ids]
        while len(level) > 1:
            if len(level) % 2: level.append(level[-1])
            level = [sha256d(level[i] + level[i+1]) for i in range(0, len(level), 2)]
        expected = internal_to_hex(level[0])

        # All four positions must verify against the same root
        for idx, tx in enumerate(ids):
            root, path, _ = compute_merkle_path(ids, idx)
            assert root == expected
            assert verify_path(tx, path, expected), f"index {idx} failed"

    def test_tampered_sibling_fails_verification(self):
        # A genuine proof should pass; flipping one bit in any sibling must fail
        ids = [f"{i:02x}"*32 for i in range(1, 9)]
        root, path, _ = compute_merkle_path(ids, 0)
        assert verify_path(ids[0], path, root)
        tampered = [dict(s) for s in path]
        tampered[0]["sibling"] = "ff" + tampered[0]["sibling"][2:]
        assert not verify_path(ids[0], tampered, root)


# ───────────────────────────────────────────────────────────────────────────────
# 4. Nakamoto §11 attack probability
# ───────────────────────────────────────────────────────────────────────────────

class TestNakamoto:
    """Compare against the canonical reference points from the whitepaper."""

    # These values are from running Nakamoto's reference C code with double
    # precision. Verified cross-implementation against 50-digit mpmath.
    REFERENCE = [
        (0.10,  0,  1.0000000),
        (0.10,  5,  0.0009137),
        (0.10, 10,  0.0000012),
        (0.30,  5,  0.1773523),
        (0.30, 10,  0.0416605),
        (0.30, 50,  0.0000006),
    ]

    @pytest.mark.parametrize("q,z,expected", REFERENCE)
    def test_matches_reference(self, q, z, expected):
        got = attack_success_probability(q, z)
        assert got == pytest.approx(expected, abs=1e-6), \
            f"q={q} z={z}: got {got}, expected {expected}"

    def test_majority_attacker_succeeds_with_probability_one(self):
        for z in range(0, 20, 3):
            assert attack_success_probability(0.5,  z) == 1.0
            assert attack_success_probability(0.51, z) == 1.0
            assert attack_success_probability(0.99, z) == 1.0

    def test_probability_monotonically_decreasing_in_z(self):
        # Fix q=0.10; P(catch up) must monotonically decrease as z grows
        probs = [attack_success_probability(0.10, z) for z in range(0, 20)]
        assert all(probs[i] >= probs[i+1] for i in range(len(probs)-1))

    def test_zero_hashrate_attacker_never_succeeds(self):
        for z in [1, 5, 10, 50]:
            assert attack_success_probability(0.0, z) == 0.0


# ───────────────────────────────────────────────────────────────────────────────
# 5. Live network checks  (skipped if API is unreachable)
# ───────────────────────────────────────────────────────────────────────────────

def _api_reachable():
    try:
        r = requests.get(f"{BASE_URL}/blocks/tip/height", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.live
@pytest.mark.skipif(not _api_reachable(),
                    reason="mempool.space API unreachable; skipping live test")
class TestLive:
    """End-to-end checks that close the loop between theory and real Bitcoin."""

    def test_live_block_hash_reproduces_from_raw_header(self):
        """Most important test: prove SHA256² of raw header == API-reported hash."""
        block = get_latest_block()
        raw = get_raw_header(block["id"])
        assert len(raw) == 80, f"Header length {len(raw)} != 80"
        recomputed = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[::-1].hex()
        assert recomputed == block["id"], \
            f"Hash mismatch on block #{block['height']}"

    def test_live_block_hash_is_below_target(self):
        block = get_latest_block()
        target = bits_to_target(block["bits"])
        hash_int = int(block["id"], 16)
        assert hash_int < target, "API block fails PoW check!"

    def test_live_header_fields_match_api(self):
        block = get_latest_block()
        raw = get_raw_header(block["id"])
        version    = struct.unpack_from("<I", raw,  0)[0]
        prev_hash  = raw[ 4:36][::-1].hex()
        merkle     = raw[36:68][::-1].hex()
        timestamp  = struct.unpack_from("<I", raw, 68)[0]
        bits       = struct.unpack_from("<I", raw, 72)[0]
        nonce      = struct.unpack_from("<I", raw, 76)[0]
        assert prev_hash == block["previousblockhash"]
        assert merkle    == block["merkle_root"]
        assert timestamp == block["timestamp"]
        assert bits      == block["bits"]
        assert nonce     == block["nonce"]

    def test_live_merkle_root_recomputes(self):
        """Recompute the Merkle root of a live block from its txids."""
        block = get_latest_block()
        txids = requests.get(f"{BASE_URL}/block/{block['id']}/txids",
                              timeout=30).json()
        recomputed, path, _ = compute_merkle_path(txids, 0)
        assert recomputed == block["merkle_root"]
        # SPV-style independent verification of the coinbase
        assert verify_path(txids[0], path, block["merkle_root"])
