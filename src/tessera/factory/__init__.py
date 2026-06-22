# src/tessera/factory/__init__.py
"""The scenario-factory: deterministic seeded meridian variants (contamination mitigation)."""
from __future__ import annotations

from tessera.factory.generate import CANONICAL_SEED, generate_variant
from tessera.factory.schema import FACTORY_VERSION

__all__ = ["generate_variant", "CANONICAL_SEED", "FACTORY_VERSION"]
