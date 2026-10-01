"""Neural model lifecycle management and user library vectorization (WP-042, ADR-029).

Provides thread-safe model status discovery, background streaming download with
cryptographic SHA-256 verification against PROVENANCE.md, and local on-device
vectorization of user library content (EGW, commentaries, personal notes)
into isolated storage (data/library_embeddings.db).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Optional, Sequence
import urllib.request

import numpy as np

from search.dbaccess import connect_db_reader
from search.linking.onnx_embedder import OnnxEmbedder, find_local_model_files
from search.resource import (
    get_data_dir,
    get_embeddings_db_path,
    get_library_embeddings_db_path,
    get_models_dir,
)

logger = logging.getLogger(__name__)

# Pinned model metadata from data/PROVENANCE.md (Section 8)
DEFAULT_NEURAL_MODEL_NAME = "multilingual-e5-small"
DEFAULT_NEURAL_MODEL_PIN = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
DEFAULT_NEURAL_BASE_URL = f"https://huggingface.co/Xenova/multilingual-e5-small/resolve/{DEFAULT_NEURAL_MODEL_PIN}"
DEFAULT_ONNX_URL = f"{DEFAULT_NEURAL_BASE_URL}/onnx/model_quantized.onnx"
DEFAULT_TOK_URL = f"{DEFAULT_NEURAL_BASE_URL}/tokenizer.json"

EXPECTED_ONNX_SHA256 = "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193"
EXPECTED_TOK_SHA256 = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"

# Estimated total download size (~130 MB)
EXPECTED_TOTAL_DOWNLOAD_BYTES = 136_239_418


class NeuralModelManager:
    """Coordinates local neural model inspection, streaming download, and library vectorization."""

    def __init__(
        self,
        study_service: Any = None,
        model_name: str = DEFAULT_NEURAL_MODEL_NAME,
        models_dir: Optional[Path] = None,
    ) -> None:
        self.study = study_service
        self.model_name = model_name
        self._models_dir = Path(models_dir).resolve() if models_dir else None
        self._scripture_count_cache: Optional[int] = None

        self._download_lock = threading.Lock()
        self._download_thread: Optional[threading.Thread] = None
        self._download_state: dict[str, Any] = {
            "in_progress": False,
            "percent": 0.0,
            "downloaded_bytes": 0,
            "total_bytes": EXPECTED_TOTAL_DOWNLOAD_BYTES,
            "current_file": "",
            "error": None,
        }

        self._vectorize_lock = threading.Lock()
        self._vectorize_thread: Optional[threading.Thread] = None
        self._vectorize_state: dict[str, Any] = {
            "is_running": False,
            "total": 0,
            "processed": 0,
            "percent": 0.0,
            "eta_seconds": 0.0,
            "error": None,
        }

    @property
    def models_dir(self) -> Path:
        return self._models_dir or get_models_dir()

    def get_model_files(self) -> tuple[Optional[Path], Optional[Path]]:
        """Return paths to (model_path, tokenizer_path) if found locally."""
        if self._models_dir is not None:
            m_path, t_path = find_local_model_files(model_dir=self._models_dir, model_name=self.model_name)
            base = self._models_dir.resolve()
            if m_path and not m_path.resolve().is_relative_to(base):
                m_path = None
            if t_path and not t_path.resolve().is_relative_to(base):
                t_path = None
            return m_path, t_path
        return find_local_model_files(model_dir=self.models_dir, model_name=self.model_name)

    def is_model_available(self) -> bool:
        """Check if both model_quantized.onnx and tokenizer.json are present."""
        m_path, t_path = self.get_model_files()
        return bool(m_path and m_path.is_file() and t_path and t_path.is_file())

    def get_scripture_embeddings_count(self) -> int:
        """Count pre-computed Scripture verses in data/embeddings.db."""
        if self._scripture_count_cache is not None:
            return self._scripture_count_cache
        emb_path = get_embeddings_db_path()
        if not emb_path.is_file():
            return 0
        try:
            conn = connect_db_reader(emb_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM verses")
                row = cur.fetchone()
                count = int(row[0]) if row else 0
                if count > 0:
                    self._scripture_count_cache = count
                return count
            finally:
                conn.close()
        except Exception as exc:
            logger.debug(f"Could not read scripture embeddings count: {exc}")
            return 0

    def get_user_library_embeddings_count(self) -> int:
        """Count vectorized user paragraphs in data/library_embeddings.db."""
        lib_path = get_library_embeddings_db_path()
        if not lib_path.is_file():
            return 0
        try:
            conn = connect_db_reader(lib_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM paragraphs")
            row = cur.fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception as exc:
            logger.debug(f"Could not read library embeddings count: {exc}")
            return 0

    def get_model_status(self) -> dict[str, Any]:
        """Return comprehensive status for neural models and vector databases."""
        m_path, t_path = self.get_model_files()
        available = bool(m_path and m_path.is_file() and t_path and t_path.is_file())
        size_mb = 0.0
        if available and m_path and t_path:
            try:
                total_bytes = m_path.stat().st_size + t_path.stat().st_size
                size_mb = round(total_bytes / (1024 * 1024), 1)
            except OSError:
                size_mb = 0.0

        with self._download_lock:
            dl_progress = dict(self._download_state)
        with self._vectorize_lock:
            vec_progress = dict(self._vectorize_state)

        return {
            "status": "ok",
            "model_available": available,
            "model_name": self.model_name,
            "model_size_mb": size_mb,
            "download_in_progress": dl_progress["in_progress"],
            "download_percent": dl_progress["percent"],
            "download_error": dl_progress["error"],
            "scripture_embeddings_count": self.get_scripture_embeddings_count(),
            "user_library_embeddings_count": self.get_user_library_embeddings_count(),
            "library_vectorize_in_progress": vec_progress["is_running"],
            "library_vectorize_percent": vec_progress["percent"],
            "library_vectorize_error": vec_progress["error"],
        }

    def get_download_progress(self) -> dict[str, Any]:
        with self._download_lock:
            return dict(self._download_state)

    def get_vectorize_progress(self) -> dict[str, Any]:
        with self._vectorize_lock:
            return dict(self._vectorize_state)

    def start_model_download(self) -> dict[str, Any]:
        """Initiate background streaming download of pinned model weights with SHA-256 verification."""
        with self._download_lock:
            if self._download_state["in_progress"]:
                return {
                    "status": "already_in_progress",
                    "message": "Download is already running.",
                    "progress": dict(self._download_state),
                }

            if self.is_model_available():
                return {
                    "status": "already_installed",
                    "message": "Model weights are already installed and verified.",
                }

            self._download_state = {
                "in_progress": True,
                "percent": 0.0,
                "downloaded_bytes": 0,
                "total_bytes": EXPECTED_TOTAL_DOWNLOAD_BYTES,
                "current_file": "Initializing...",
                "error": None,
            }

            self._download_thread = threading.Thread(
                target=self._run_download_worker,
                daemon=True,
                name="NeuralModelDownloadWorker",
            )
            self._download_thread.start()

            return {
                "status": "started",
                "message": "Model download initiated in background.",
            }

    def _run_download_worker(self) -> None:
        """Background worker that streams and cryptographically verifies model assets."""
        target_dir = self.models_dir / self.model_name
        target_dir.mkdir(parents=True, exist_ok=True)

        assets = [
            ("tokenizer.json", DEFAULT_TOK_URL, EXPECTED_TOK_SHA256, target_dir / "tokenizer.json"),
            ("model_quantized.onnx", DEFAULT_ONNX_URL, EXPECTED_ONNX_SHA256, target_dir / "model_quantized.onnx"),
        ]

        total_downloaded = 0
        chunk_size = 64 * 1024  # 64 KB chunks

        try:
            for fname, url, expected_sha, dest_path in assets:
                with self._download_lock:
                    self._download_state["current_file"] = fname

                tmp_path = dest_path.with_suffix(".tmp")
                hasher = hashlib.sha256()

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "AdventistBibleStudy/1.0 (offline-first)"},
                )

                try:
                    with urllib.request.urlopen(req, timeout=45) as resp, open(tmp_path, "wb") as f_out:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            hasher.update(chunk)
                            total_downloaded += len(chunk)

                            pct = min(99.0, round((total_downloaded / EXPECTED_TOTAL_DOWNLOAD_BYTES) * 100.0, 1))
                            with self._download_lock:
                                self._download_state["downloaded_bytes"] = total_downloaded
                                self._download_state["percent"] = pct

                    actual_sha = hasher.hexdigest().lower()
                    if actual_sha != expected_sha.lower():
                        raise ValueError(
                            f"Cryptographic hash mismatch for {fname}: "
                            f"expected {expected_sha}, got {actual_sha} (per PROVENANCE.md)"
                        )

                    # Move verified file atomically into place
                    tmp_path.replace(dest_path)
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)

            with self._download_lock:
                self._download_state.update({
                    "in_progress": False,
                    "percent": 100.0,
                    "downloaded_bytes": EXPECTED_TOTAL_DOWNLOAD_BYTES,
                    "current_file": "Ready",
                    "error": None,
                })

        except Exception as exc:
            logger.error(f"Neural model download failed: {exc}", exc_info=True)
            with self._download_lock:
                self._download_state.update({
                    "in_progress": False,
                    "error": str(exc),
                })

    def start_library_vectorization(self, batch_size: int = 32, force: bool = False) -> dict[str, Any]:
        """Initiate background vectorization of imported user library paragraphs."""
        if not self.is_model_available():
            raise RuntimeError("Neural model is not installed. Please download the model first.")

        if not self.study or not getattr(self.study, "egw_db", None) or not self.study.egw_db.exists():
            raise ValueError("No library content found in egw.db to vectorize. Please import books or commentary first.")

        with self._vectorize_lock:
            if self._vectorize_state["is_running"]:
                return {
                    "status": "already_running",
                    "message": "Vectorization is already in progress.",
                    "progress": dict(self._vectorize_state),
                }

            self._vectorize_state = {
                "is_running": True,
                "total": 0,
                "processed": 0,
                "percent": 0.0,
                "eta_seconds": 0.0,
                "error": None,
            }

            self._vectorize_thread = threading.Thread(
                target=self._run_vectorize_worker,
                args=(batch_size, force),
                daemon=True,
                name="LibraryVectorizeWorker",
            )
            self._vectorize_thread.start()

            return {
                "status": "started",
                "message": "Library vectorization initiated in background.",
            }

    def _run_vectorize_worker(self, batch_size: int = 32, force: bool = False) -> None:
        """Background worker that computes dense vectors and inserts them into library_embeddings.db."""
        lib_path = get_library_embeddings_db_path()
        lib_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Query paragraphs from egw.db
            egw_path = self.study.egw_db.db_path
            conn_egw = connect_db_reader(egw_path)
            cur_egw = conn_egw.cursor()
            cur_egw.execute(
                "SELECT id, book_code, book_title, chapter_title, text "
                "FROM egw_paragraphs ORDER BY rowid"
            )
            all_rows = cur_egw.fetchall()
            conn_egw.close()

            if not all_rows:
                with self._vectorize_lock:
                    self._vectorize_state.update({
                        "is_running": False,
                        "total": 0,
                        "processed": 0,
                        "percent": 100.0,
                        "eta_seconds": 0.0,
                        "error": None,
                    })
                return

            # Open or initialize library_embeddings.db
            conn_lib = sqlite3.connect(lib_path)
            try:
                conn_lib.execute("PRAGMA journal_mode = WAL")
                conn_lib.execute("PRAGMA synchronous = NORMAL")
                conn_lib.execute("""
                    CREATE TABLE IF NOT EXISTS paragraphs (
                        paragraph_id TEXT PRIMARY KEY,
                        book_code TEXT,
                        vector BLOB NOT NULL,
                        magnitude REAL NOT NULL
                    )
                """)
                conn_lib.execute("""
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)

                existing_ids: set[str] = set()
                if not force:
                    cur_lib = conn_lib.cursor()
                    cur_lib.execute("SELECT paragraph_id FROM paragraphs")
                    existing_ids = {r[0] for r in cur_lib.fetchall()}

                to_process = [r for r in all_rows if r[0] not in existing_ids] if not force else all_rows
                total_count = len(to_process)

                if total_count == 0:
                    with self._vectorize_lock:
                        self._vectorize_state.update({
                            "is_running": False,
                            "total": len(all_rows),
                            "processed": len(all_rows),
                            "percent": 100.0,
                            "eta_seconds": 0.0,
                            "error": None,
                        })
                    return

                with self._vectorize_lock:
                    self._vectorize_state.update({
                        "is_running": True,
                        "total": total_count,
                        "processed": 0,
                        "percent": 0.0,
                        "eta_seconds": 0.0,
                        "error": None,
                    })

                embedder = OnnxEmbedder(strict=True)
                if not embedder.available():
                    raise RuntimeError("OnnxEmbedder runtime or weights could not be initialized.")

                batch_size = max(1, min(batch_size, 128))
                processed_count = 0
                t0 = time.perf_counter()

                for start_idx in range(0, total_count, batch_size):
                    chunk = to_process[start_idx : start_idx + batch_size]
                    passage_texts: list[str] = []
                    chunk_meta: list[tuple[str, str]] = []

                    for pid, bcode, btitle, ch_title, ptext in chunk:
                        clean_text = (ptext or "").strip()
                        hdr = f"{btitle} - {ch_title}" if ch_title else btitle
                        passage_texts.append(f"passage: {hdr}: {clean_text}")
                        chunk_meta.append((pid, bcode))

                    vectors = embedder.embed_batch(passage_texts, is_query=False, batch_size=batch_size)

                    rows_to_insert = []
                    for i, (pid, bcode) in enumerate(chunk_meta):
                        vec = vectors[i]
                        mag = float(np.linalg.norm(vec))
                        rows_to_insert.append((pid, bcode, vec.tobytes(), mag))

                    conn_lib.executemany(
                        "INSERT OR REPLACE INTO paragraphs (paragraph_id, book_code, vector, magnitude) VALUES (?, ?, ?, ?)",
                        rows_to_insert,
                    )
                    conn_lib.commit()

                    processed_count += len(chunk)
                    elapsed = time.perf_counter() - t0
                    rate = processed_count / max(elapsed, 0.001)
                    remaining = total_count - processed_count
                    eta = round(remaining / max(rate, 0.001), 1)
                    pct = round((processed_count / total_count) * 100.0, 1)

                    with self._vectorize_lock:
                        self._vectorize_state.update({
                            "is_running": True,
                            "total": total_count,
                            "processed": processed_count,
                            "percent": pct,
                            "eta_seconds": eta,
                        })

                # Record final metadata
                cur = conn_lib.cursor()
                cur.execute("SELECT COUNT(*) FROM paragraphs")
                final_count = cur.fetchone()[0]
                conn_lib.executemany(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    [
                        ("model", embedder.model_name),
                        ("dimension", str(embedder.dim)),
                        ("updated_at", datetime.now(timezone.utc).isoformat()),
                        ("total_paragraphs", str(final_count)),
                    ],
                )
                conn_lib.commit()
            finally:
                conn_lib.close()

            with self._vectorize_lock:
                self._vectorize_state.update({
                    "is_running": False,
                    "total": total_count,
                    "processed": total_count,
                    "percent": 100.0,
                    "eta_seconds": 0.0,
                    "error": None,
                })

        except Exception as exc:
            logger.error(f"Library vectorization failed: {exc}", exc_info=True)
            with self._vectorize_lock:
                self._vectorize_state.update({
                    "is_running": False,
                    "error": str(exc),
                })
