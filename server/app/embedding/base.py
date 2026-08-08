"""Embedder abstraction and registry.

Embedders must be safe to import even if their optional dependency is
missing; raise ``EmbedderError`` only at instantiation time.
"""
from __future__ import annotations

import abc
from typing import Iterable

from pydantic import BaseModel, Field


class EmbedderError(RuntimeError):
    """Raised when an embedder cannot produce vectors."""


class EmbedderConfig(BaseModel):
    name: str
    type: str
    options: dict = Field(default_factory=dict)


class Embedder(abc.ABC):
    """Abstract text → vector encoder."""

    name: str
    type: str
    dim: int

    def __init__(self, config: EmbedderConfig) -> None:
        self.config = config
        self.name = config.name or self.type

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode ``texts`` into vectors of length ``dim``."""

    async def health(self) -> bool:
        """Default health probe: embed a tiny string and check dim."""
        v = await self.embed(["ok"])
        return bool(v) and len(v[0]) == self.dim


# ---- Registry ---------------------------------------------------------------

_REGISTRY: dict[str, type[Embedder]] = {}


def register_embedder(type_name: str, cls: type[Embedder]) -> None:
    if type_name in _REGISTRY:
        raise ValueError(f"embedder type {type_name!r} already registered")
    _REGISTRY[type_name] = cls


def get_embedder_cls(type_name: str) -> type[Embedder]:
    if type_name not in _REGISTRY:
        raise EmbedderError(f"unknown embedder type: {type_name}")
    return _REGISTRY[type_name]


def list_embedder_types() -> list[str]:
    return sorted(_REGISTRY)