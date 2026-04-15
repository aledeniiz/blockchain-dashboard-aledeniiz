"""
api/blockchain_client.py
Session 1 — Milestone 2: First API call to Bitcoin blockchain data.

APIs used (both free, no API key required):
  Primary  : https://mempool.space/api   (faster, more reliable)
  Fallback : https://blockstream.info/api

Key endpoints:
  GET /blocks/tip/height          -> latest block height (integer)
  GET /blocks/tip/hash            -> latest block hash
  GET /block/:hash                -> full block data
  GET /block/:hash/header         -> raw 80-byte header (hex)
  GET /block-height/:height       -> block hash at given height
  GET /blocks/:start_height       -> list of 10 blocks from height

Block fields we use:
  - id (hash)        : 256-bit SHA256d hash of the header (reversed byte order)
  - height           : block number in the chain
  - timestamp        : UNIX timestamp (seconds)
  - bits             : compact encoding of the Proof-of-Work target threshold
  - nonce            : the value miners iterated to find a valid hash
  - tx_count         : number of transactions in the block
  - size / weight    : block size metrics

IMPORTANT — bits field and the target:
  The 'bits' field is the compact (nBits) encoding of the target T:
    bits = 0xAABBCCDD  ->  T = 0x00BBCCDD * 256^(0xAA - 3)
  Difficulty = genesis_target / T
  genesis_target = 0x00000000FFFF * 2^(8*26)

Observation from live data:
  Every valid block hash starts with many leading zeros (e.g. 00000000000...).
  This directly visualises Proof of Work: the miner found a nonce such that
  SHA256(SHA256(header_bytes)) < target. More leading zeros = lower target = harder puzzle.
"""

import requests

# Primary API: mempool.space (very fast and reliable)
BASE_URL = "https://mempool.space/api"
# Fallback API: blockstream.info
FALLBACK_URL = "https://blockstream.info/api"

TIMEOUT = 15  # seconds


def _get(url: str) -> requests.Response:
    """GET with fallback: tries BASE_URL first, then FALLBACK_URL."""
    # Replace base in the URL for fallback attempt
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp
    except Exception:
        fallback_url = url.replace(BASE_URL, FALLBACK_URL)
        resp = requests.get(fallback_url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp


def get_latest_block() -> dict:
    """Fetch latest block hash then return full block data."""
    tip_hash = _get(f"{BASE_URL}/blocks/tip/hash").text.strip()
    block = _get(f"{BASE_URL}/block/{tip_hash}").json()
    return block


def get_blocks(n: int = 50) -> list:
    """
    Fetch the last n blocks.
    Returns a list of block dicts sorted oldest -> newest.
    """
    tip_height = int(_get(f"{BASE_URL}/blocks/tip/height").text.strip())

    blocks = []
    start = tip_height
    while len(blocks) < n:
        batch = _get(f"{BASE_URL}/blocks/{start}").json()
        blocks.extend(batch)
        if not batch:
            break
        start = batch[-1]["height"] - 1

    blocks = blocks[:n]
    blocks.sort(key=lambda b: b["height"])
    return blocks


def get_block_at_height(height: int) -> dict:
    """Fetch a block by height."""
    block_hash = _get(f"{BASE_URL}/block-height/{height}").text.strip()
    return _get(f"{BASE_URL}/block/{block_hash}").json()


def get_raw_header(block_hash: str) -> bytes:
    """Fetch the raw 80-byte block header (returned as hex by the API)."""
    return bytes.fromhex(_get(f"{BASE_URL}/block/{block_hash}/header").text.strip())


def bits_to_target(bits_hex) -> int:
    """
    Convert the compact 'bits' field to the full 256-bit target integer.
    bits_hex can be a hex string like '0x1702eb48' or a plain int.
    """
    bits = int(bits_hex, 16) if isinstance(bits_hex, str) else bits_hex
    exponent = bits >> 24
    coefficient = bits & 0x007FFFFF
    return coefficient * (256 ** (exponent - 3))


def bits_to_difficulty(bits_hex) -> float:
    """Convert 'bits' to the Bitcoin difficulty value."""
    GENESIS_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
    target = bits_to_target(bits_hex)
    return GENESIS_TARGET / target if target else 0.0


if __name__ == "__main__":
    print("Fetching latest Bitcoin block...")
    block = get_latest_block()

    leading_zeros = len(block["id"]) - len(block["id"].lstrip("0"))
    target = bits_to_target(block["bits"])
    difficulty = bits_to_difficulty(block["bits"])

    print(f"\n{'='*50}")
    print(f"  Latest Bitcoin Block")
    print(f"{'='*50}")
    print(f"  Height    : {block['height']}")
    print(f"  Hash      : {block['id']}")
    print(f"  Leading 0s: {leading_zeros} hex digits = ~{leading_zeros * 4} bits")
    print(f"  Timestamp : {block['timestamp']}")
    print(f"  Nonce     : {block['nonce']}")
    print(f"  Bits      : {hex(block['bits'])}")
    print(f"  Target    : {hex(target)}")
    print(f"  Difficulty: {difficulty:,.0f}")
    print(f"  Tx count  : {block['tx_count']}")
    print(f"\n  Observation: The hash starts with {leading_zeros} leading zero hex digits.")
    print("  This confirms Proof of Work: the miner iterated the nonce until")
    print("  SHA256(SHA256(header)) < target (= the difficulty threshold).")
    print(f"\n  The bits field {hex(block['bits'])} encodes the target in compact form:")
    print(f"    exponent  = {block['bits'] >> 24}")
    print(f"    coefficient = {hex(block['bits'] & 0x007FFFFF)}")
    print(f"    target    = coefficient * 256^(exponent-3) = {hex(target)}")
