"""Hash-based deterministic mock embedder used in tests.

The mock produces a stable vector for any input by hashing tokens into a fixed
vocabulary. Vectors are unit-normalized so cosine similarity behaves like an
embedding model. Useful for end-to-end tests without loading model weights.
"""
from __future__ import annotations

import hashlib
import math

from app.embedding.base import Embedder, EmbedderConfig, register_embedder


class HashMockEmbedder(Embedder):
    type = "mock-hash"
    dim = 64

    def __init__(self, config: EmbedderConfig) -> None:
        super().__init__(config)
        opts = config.options
        self.dim = int(opts.get("dim", 64))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vec(t, self.dim) for t in texts]


def _hash_vec(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


register_embedder("mock-hash", HashMockEmbedder)