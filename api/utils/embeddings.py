"""Embedding generation utilities.

We use a hashing-vectorizer fallback by default so the system works
out-of-the-box. Production deployments should plug in a real multilingual
embedding model (e.g. Voyage AI ``voyage-multilingual-2`` or
``text-embedding-3-large``) by overriding ``generate_embedding``.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from api.core.config import get_settings
from api.utils.arabic import normalize_arabic


def _hash_token(token: str, salt: int, dim: int) -> int:
    h = hashlib.blake2b(f"{salt}:{token}".encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") % dim


def generate_embedding(text: str, *, dim: int | None = None) -> list[float]:
    """Generate a deterministic, length-normalized vector for ``text``.

    This default uses a hashing trigram-vectorizer. It is **not** a true
    semantic model, but it provides stable behavior for tests and is good
    enough to demonstrate the pipeline end-to-end.
    """
    if dim is None:
        dim = get_settings().embedding_dimension
    if dim <= 0:
        raise ValueError("dim must be positive")

    normalized = normalize_arabic(text)
    if not normalized:
        return [0.0] * dim

    tokens = normalized.split()
    trigrams: list[str] = []
    for token in tokens:
        padded = f"  {token} "
        for i in range(len(padded) - 2):
            trigrams.append(padded[i : i + 3])
    if not trigrams:
        trigrams = tokens

    vec = [0.0] * dim
    for tg in trigrams:
        idx = _hash_token(tg, 1, dim)
        sign = 1.0 if _hash_token(tg, 2, dim) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have the same dimension")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
