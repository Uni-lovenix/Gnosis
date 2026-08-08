"""Package init."""
from app.embedding.base import (
    Embedder,
    EmbedderError,
    get_embedder_cls,
    list_embedder_types,
    register_embedder,
)
from app.embedding.bge_m3 import BGEM3Embedder
from app.embedding.openai_compat import OpenAICompatEmbedder
from app.embedding.mock_embedder import HashMockEmbedder

__all__ = [
    "Embedder",
    "EmbedderError",
    "register_embedder",
    "get_embedder_cls",
    "list_embedder_types",
    "BGEM3Embedder",
    "OpenAICompatEmbedder",
    "HashMockEmbedder",
]