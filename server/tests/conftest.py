"""Pytest configuration.

Pin test runs to the deterministic in-memory embedder so:

* No external service (Ollama, sentence-transformers, network) is touched.
* ``app.main.create_app()`` does not log ``embedder.fallback_to_mock`` and
  does not attempt any localhost connection.
* CI stays fast (~3s) and reproducible.

See ``docs/RUNBOOK.md`` §"Embedder defaults" for the production default
(Ollama bge-m3) and how to opt back in for manual ``npm run eval:ollama``.
"""
import os
import sys
from pathlib import Path

# Force the production embedder default to mock before any app module
# imports ``Settings()``. ``env_file=None`` in Settings means we must write
# through ``os.environ``.
os.environ.setdefault("KB_EMBED_BACKEND", "mock-hash")
os.environ.setdefault("KB_EMBED_DIM", "1024")

# Allow `import app...` from the tests directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
