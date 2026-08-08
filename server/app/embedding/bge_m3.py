"""BGE-M3 embedder (local) using sentence-transformers or FlagEmbedding.

We default to sentence-transformers; FlagEmbedding can be selected by setting
``backend: "flagembedding"`` in the embedder options. The model is loaded
lazily on first ``embed`` call to keep import fast.
"""
from __future__ import annotations

from app.embedding.base import Embedder, EmbedderConfig, EmbedderError, register_embedder


class BGEM3Embedder(Embedder):
    type = "bge-m3"
    dim = 1024

    def __init__(self, config: EmbedderConfig) -> None:
        super().__init__(config)
        opts = config.options
        self.model_name = opts.get("model", "BAAI/bge-m3")
        self.backend = opts.get("backend", "sentence-transformers")
        self.batch_size = int(opts.get("batch_size", 16))
        self._model = None  # lazy

    def _load(self):
        if self._model is not None:
            return
        if self.backend == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError as e:  # pragma: no cover
                raise EmbedderError(
                    "sentence-transformers not installed. "
                    "`pip install -e '.[embedding-local]'`."
                ) from e
            self._model = SentenceTransformer(self.model_name)
        elif self.backend == "flagembedding":
            try:
                from FlagEmbedding import BGEM3FlagModel  # type: ignore
            except ImportError as e:  # pragma: no cover
                raise EmbedderError(
                    "FlagEmbedding not installed. "
                    "`pip install -e '.[embedding-local]'`."
                ) from e
            self._model = BGEM3FlagModel(self.model_name, use_fp16=False)
        else:
            raise EmbedderError(f"unknown backend: {self.backend}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if self.backend == "sentence-transformers":
            vecs = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return [v.tolist() for v in vecs]
        # FlagEmbedding path
        vecs = self._model.encode(texts, batch_size=self.batch_size, max_length=8192)
        return [v.tolist() for v in vecs]


register_embedder("bge-m3", BGEM3Embedder)