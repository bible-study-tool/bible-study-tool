"""Pluggable multilingual embedder.

Design goals
------------
* **Offline-first**: everything works with no network and no heavy model.
* **Deterministic fallback**: when no ML model is installed, use a
  cross-script character n-gram hashing embedder (numpy-only). This is
  fully reproducible and hash-grounded, matching the project's "AI layer
  requires human review" boundary.
* **Upgrade path**: if `sentence-transformers` is importable, prefer a real
  multilingual model (e.g. `intfloat/multilingual-e5-small`) so that
  Hebrew / Greek / English land in one shared vector space.

The embedder returns numpy float vectors on the same interface so the rest
of the pipeline is model-agnostic.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import numpy as np

_DEFAULT_MODEL = "intfloat/multilingual-e5-small"

# Unicode ranges we care about per script, used by the fallback to normalize.
_SCRIPT_RE = {
    "hebrew": re.compile(r"[\u0590-\u05ff]"),
    "greek": re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]"),
    "latin": re.compile(r"[a-zA-Z]"),
}


@dataclass
class Embedding:
    """A vector plus the surface text it was computed from."""

    text: str
    vector: np.ndarray


class BaseEmbedder:
    name = "base"

    def embed(self, text: str) -> np.ndarray:
        raise NotImplementedError

    def available(self) -> bool:
        return True


class CharNgramEmbedder(BaseEmbedder):
    """Deterministic, offline, cross-script character n-gram embedder.

    Works on any script (Hebrew, Greek, Latin) because it operates on
    characters, not language-specific tokens. Produces a fixed-size
    hashed bag-of-ngrams vector in [0, 1] (L2-normalized).
    """

    name = "char-ngram"

    def __init__(self, dim: int = 512, n_min: int = 2, n_max: int = 4):
        self.dim = dim
        self.n_min = n_min
        self.n_max = n_max

    def _normalize(self, text: str) -> str:
        # Lowercase, strip diacritics via simple NFKD-style folding is not
        # available without unicodedata at runtime cost; keep it cheap and
        # just normalize whitespace and case.
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _ngrams(self, text: str):
        norm = self._normalize(text)
        pad = self.n_max - 1
        # Use explicit-space padding so short strings still produce ngrams.
        padded = " " * pad + norm + " " * pad
        for n in range(self.n_min, self.n_max + 1):
            for i in range(len(padded) - n + 1):
                yield padded[i : i + n]

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for gram in self._ngrams(text):
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest, "little") % self.dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


class SentenceTransformerEmbedder(CharNgramEmbedder):
    """Real multilingual transformer embedder (best fidelity).

    Only used when `sentence-transformers` (and its deps) are importable.
    Falls back to the deterministic n-gram embedder on any failure.
    """

    name = "sentence-transformers"

    def __init__(self, model_name: str = _DEFAULT_MODEL, **kw):
        super().__init__(**kw)
        self.model_name = model_name
        self._model = None
        self._load()

    def _load(self):
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        except Exception:
            self._model = None

    def available(self) -> bool:
        return self._model is not None

    def embed(self, text: str) -> np.ndarray:
        if self._model is None:
            return super().embed(text)
        return np.asarray(self._model.encode(text, normalize_embeddings=True), dtype=np.float32)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


def get_embedder(prefer_model: bool = True) -> BaseEmbedder:
    """Return the best available embedder.

    Priority (ADR-029):
    1. Zero-PyTorch OnnxEmbedder (fast local ONNX CPU inference)
    2. SentenceTransformerEmbedder (if PyTorch/sentence-transformers installed)
    3. Deterministic CharNgramEmbedder (offline zero-dependency fallback)
    """
    if prefer_model:
        try:
            from search.linking.onnx_embedder import OnnxEmbedder

            onnx_emb = OnnxEmbedder()
            if onnx_emb.available():
                return onnx_emb
        except Exception:
            pass

        st = SentenceTransformerEmbedder()
        if st.available():
            return st

    return CharNgramEmbedder()
