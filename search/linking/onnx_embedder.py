"""Lightweight zero-PyTorch local ONNX query embedder (ADR-029, WP-040).

Runs INT8 quantized multilingual Transformer models (default: multilingual-e5-small)
via onnxruntime and tokenizers on standard CPU with ~10ms latency and <40 MB RAM.
Strictly falls back to CharNgramEmbedder when ONNX runtime or model weights are unavailable.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
from typing import Any, Optional, Sequence

import numpy as np

from search.linking.embedder import BaseEmbedder, CharNgramEmbedder
from search.resource import get_models_dir

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_NAME = "multilingual-e5-small"
_DEFAULT_DIM = 384
_DEFAULT_MAX_LEN = 512


def find_local_model_files(
    model_dir: Optional[Path] = None,
    model_name: str = _DEFAULT_MODEL_NAME,
) -> tuple[Optional[Path], Optional[Path]]:
    """Locate the ONNX model file and tokenizer.json for a model."""
    search_dirs: list[Path] = []
    if model_dir is not None:
        p = Path(model_dir)
        search_dirs.append(p / model_name)
        search_dirs.append(p)

    configured_models_dir = get_models_dir()
    search_dirs.append(configured_models_dir / model_name)
    search_dirs.append(configured_models_dir)

    # Check HuggingFace hub cache if present
    hf_cache_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))
    if hf_cache_home.is_dir():
        for candidate in [
            hf_cache_home / f"models--Xenova--{model_name}" / "snapshots",
            hf_cache_home / f"models--intfloat--{model_name}" / "snapshots",
        ]:
            if candidate.is_dir():
                for snap in candidate.iterdir():
                    if snap.is_dir():
                        search_dirs.append(snap)
                        search_dirs.append(snap / "onnx")

    onnx_candidates = [
        "model_quantized.onnx",
        "model_int8.onnx",
        "model_qint8_avx512_vnni.onnx",
        "model.onnx",
    ]

    model_path: Optional[Path] = None
    tokenizer_path: Optional[Path] = None

    for d in search_dirs:
        if not d.is_dir():
            continue
        # Search for ONNX model
        if model_path is None:
            for c in onnx_candidates:
                cand = d / c
                if cand.is_file():
                    model_path = cand
                    break
                # Also check subfolder onnx/
                cand_sub = d / "onnx" / c
                if cand_sub.is_file():
                    model_path = cand_sub
                    break

        # Search for tokenizer.json
        if tokenizer_path is None:
            cand_tok = d / "tokenizer.json"
            if cand_tok.is_file():
                tokenizer_path = cand_tok
            elif (d / "onnx" / "tokenizer.json").is_file():
                tokenizer_path = d / "onnx" / "tokenizer.json"

        if model_path is not None and tokenizer_path is not None:
            break

    return model_path, tokenizer_path


class OnnxEmbedder(BaseEmbedder):
    """Zero-PyTorch multilingual neural embedder running on CPU via ONNX Runtime."""

    name = "onnx-multilingual-e5-small"

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        tokenizer_path: Optional[str | Path] = None,
        model_name: str = _DEFAULT_MODEL_NAME,
        dim: int = _DEFAULT_DIM,
        max_length: int = _DEFAULT_MAX_LEN,
        is_e5: bool = True,
        strict: bool = False,
    ) -> None:
        self.model_name = model_name
        self.dim = dim
        self.max_length = max_length
        self.is_e5 = is_e5
        self.strict = strict

        self._model_path = Path(model_path).resolve() if model_path else None
        self._tokenizer_path = Path(tokenizer_path).resolve() if tokenizer_path else None

        self._fallback = CharNgramEmbedder(dim=self.dim)
        self._session: Any = None
        self._session_input_names: set[str] = set()
        self._tokenizer: Any = None
        self._lock = threading.Lock()
        self._load_attempted: bool = False
        self._is_available: bool = False

    def _resolve_paths(self) -> None:
        if self._model_path is None or self._tokenizer_path is None:
            m_path, t_path = find_local_model_files(model_name=self.model_name)
            if self._model_path is None:
                self._model_path = m_path
            if self._tokenizer_path is None:
                self._tokenizer_path = t_path

    def _init_engine(self) -> bool:
        with self._lock:
            if self._load_attempted:
                return self._is_available

            self._load_attempted = True
            self._resolve_paths()

            if self._model_path is None or not self._model_path.is_file():
                logger.debug(f"ONNX model file for '{self.model_name}' not found.")
                return False

            if self._tokenizer_path is None or not self._tokenizer_path.is_file():
                logger.debug(f"Tokenizer file for '{self.model_name}' not found.")
                return False

            try:
                import onnxruntime as ort
                from tokenizers import Tokenizer
            except ImportError as exc:
                logger.debug(f"onnxruntime or tokenizers not installed: {exc}")
                return False

            try:
                # Configure fast CPU session options
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = max(1, min(os.cpu_count() or 4, 8))
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.log_severity_level = 3  # Error only

                self._session = ort.InferenceSession(
                    str(self._model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self._session_input_names = {inp.name for inp in self._session.get_inputs()}

                tok = Tokenizer.from_file(str(self._tokenizer_path))
                tok.enable_truncation(max_length=self.max_length)
                pad_id = tok.token_to_id("<pad>")
                if pad_id is None:
                    pad_id = 1
                tok.enable_padding(pad_id=pad_id, pad_token="<pad>")
                self._tokenizer = tok
                self._pad_id = pad_id
                self._is_available = True
                return True
            except Exception as exc:
                logger.warning(f"Failed to initialize OnnxEmbedder session: {exc}")
                self._session = None
                self._session_input_names = set()
                self._tokenizer = None
                self._is_available = False
                return False

    def available(self) -> bool:
        """Return True if ONNX runtime, tokenizer, and model weights are ready."""
        return self._init_engine()

    @property
    def model_path(self) -> Optional[Path]:
        self._resolve_paths()
        return self._model_path

    @property
    def tokenizer_path(self) -> Optional[Path]:
        self._resolve_paths()
        return self._tokenizer_path

    def _prepare_text(self, text: str, is_query: bool) -> str:
        text = text.strip()
        if not self.is_e5:
            return text
        lower = text.lower()
        if lower.startswith("query:") or lower.startswith("passage:"):
            return text
        prefix = "query: " if is_query else "passage: "
        return prefix + text

    def embed(self, text: str, is_query: bool = True) -> np.ndarray:
        """Compute a 1D dense vector for a single query or passage."""
        if not self.available():
            if self.strict:
                raise RuntimeError(f"OnnxEmbedder not available for model '{self.model_name}'")
            return self._fallback.embed(text)

        batch = self.embed_batch([text], is_query=is_query, batch_size=1)
        return batch[0]

    def embed_batch(
        self,
        texts: Sequence[str],
        is_query: bool = False,
        batch_size: int = 64,
    ) -> np.ndarray:
        """Compute 2D dense vectors for a sequence of texts."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        if not self.available():
            if self.strict:
                raise RuntimeError(f"OnnxEmbedder not available for model '{self.model_name}'")
            return np.stack([self._fallback.embed(t) for t in texts]).astype(np.float32)

        results: list[np.ndarray] = []
        n = len(texts)

        for start in range(0, n, batch_size):
            chunk = texts[start : start + batch_size]
            prepared = [self._prepare_text(t, is_query=is_query) for t in chunk]
            encodings = self._tokenizer.encode_batch(prepared)

            input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
            token_type_ids = np.zeros_like(input_ids)

            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
            # Only include token_type_ids if expected by model inputs
            if "token_type_ids" in self._session_input_names:
                inputs["token_type_ids"] = token_type_ids

            outputs = self._session.run(None, inputs)
            last_hidden_state = outputs[0]  # [cur_batch_size, max_seq_len, dim]

            # Mean pooling weighted by attention mask
            mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
            sum_embeddings = np.sum(last_hidden_state * mask_expanded, axis=1)
            sum_mask = np.maximum(mask_expanded.sum(axis=1), 1e-9)
            pooled = sum_embeddings / sum_mask

            # L2 normalization
            norm = np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            normalized = (pooled / norm).astype(np.float32)
            results.append(normalized)

        return np.vstack(results)
