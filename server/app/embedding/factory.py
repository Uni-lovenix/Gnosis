"""Embedder factory."""
from app.embedding.base import Embedder, EmbedderConfig, get_embedder_cls


def build_embedder(config: EmbedderConfig) -> Embedder:
    cls = get_embedder_cls(config.type)
    return cls(config)