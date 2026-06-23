# src/tessera/factory/commit.py
"""Salted seed-commitment for the holdout protocol (ADR-0008). A bare hash of a small
integer seed is trivially brute-forced, so the salt is what provides hiding: publish only
the commitment before a run; reveal {seed, salt, factory_version} afterward to prove the
graded instance was fixed in advance and to reproduce it."""

from __future__ import annotations

import hashlib
import os


def _digest(seed: int, salt_hex: str, factory_version: str) -> str:
    h = hashlib.sha256()
    h.update(factory_version.encode())
    h.update(b"\x00")
    h.update(str(seed).encode())
    h.update(b"\x00")
    h.update(bytes.fromhex(salt_hex))
    return h.hexdigest()


def commit(seed: int, factory_version: str) -> tuple[str, str]:
    """Return (commitment_hex, salt_hex) for a seed. The salt is a fresh 256-bit nonce."""
    salt_hex = os.urandom(32).hex()
    return _digest(seed, salt_hex, factory_version), salt_hex


def verify(commitment: str, seed: int, salt: str, factory_version: str) -> bool:
    # A non-hex / odd-length / None salt can't reproduce any commitment — fromhex raises
    # ValueError (bad hex) or TypeError (None from a deserialized reveal with a null/missing
    # field); a verifier handed a malformed reveal wants False, not an exception.
    try:
        return _digest(seed, salt, factory_version) == commitment
    except (ValueError, TypeError):
        return False
