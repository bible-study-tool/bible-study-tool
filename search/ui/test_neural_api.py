"""Integration and unit tests for neural model endpoints and vectorization (WP-042)."""

from __future__ import annotations

import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.parse
import urllib.request

import numpy as np

from search.ui import web_server
from search.ui.neural_manager import (
    DEFAULT_NEURAL_MODEL_NAME,
    EXPECTED_ONNX_SHA256,
    EXPECTED_TOK_SHA256,
    NeuralModelManager,
)
from search.ui.study_service import StudyService


class NeuralModelManagerUnitTests(unittest.TestCase):
    """Unit tests for NeuralModelManager methods in isolation."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp_dir.name)
        self.models_dir = self.data_dir / "models"
        self.models_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_status_reporting_when_unhydrated(self) -> None:
        mgr = NeuralModelManager(models_dir=self.models_dir)
        with patch("search.ui.neural_manager.get_data_dir", return_value=self.data_dir), \
             patch("search.ui.neural_manager.get_embeddings_db_path", return_value=self.data_dir / "embeddings.db"), \
             patch("search.ui.neural_manager.get_library_embeddings_db_path", return_value=self.data_dir / "library_embeddings.db"):
            status = mgr.get_model_status()
            self.assertEqual(status["status"], "ok")
            self.assertFalse(status["model_available"])
            self.assertEqual(status["model_size_mb"], 0.0)
            self.assertEqual(status["scripture_embeddings_count"], 0)
            self.assertEqual(status["user_library_embeddings_count"], 0)

    def test_status_reporting_when_hydrated(self) -> None:
        model_sub = self.models_dir / DEFAULT_NEURAL_MODEL_NAME
        model_sub.mkdir(parents=True)
        onnx_file = model_sub / "model_quantized.onnx"
        tok_file = model_sub / "tokenizer.json"
        onnx_file.write_bytes(b"x" * 1024 * 1024)  # 1 MB
        tok_file.write_bytes(b"y" * 1024 * 1024)   # 1 MB

        # Create dummy embeddings.db
        emb_db = self.data_dir / "embeddings.db"
        conn = sqlite3.connect(emb_db)
        conn.execute("CREATE TABLE verses (verse_id TEXT PRIMARY KEY, vector BLOB, magnitude REAL)")
        conn.execute("INSERT INTO verses VALUES ('Gen.1.1', ?, 1.0)", (b"\x00" * 1536,))
        conn.commit()
        conn.close()

        # Create dummy library_embeddings.db
        lib_db = self.data_dir / "library_embeddings.db"
        conn = sqlite3.connect(lib_db)
        conn.execute("CREATE TABLE paragraphs (paragraph_id TEXT PRIMARY KEY, book_code TEXT, vector BLOB, magnitude REAL)")
        conn.execute("INSERT INTO paragraphs VALUES ('p1', 'PP', ?, 1.0)", (b"\x00" * 1536,))
        conn.commit()
        conn.close()

        mgr = NeuralModelManager(models_dir=self.models_dir)
        with patch("search.ui.neural_manager.get_data_dir", return_value=self.data_dir), \
             patch("search.ui.neural_manager.get_embeddings_db_path", return_value=emb_db), \
             patch("search.ui.neural_manager.get_library_embeddings_db_path", return_value=lib_db):
            status = mgr.get_model_status()
            self.assertEqual(status["status"], "ok")
            self.assertTrue(status["model_available"])
            self.assertAlmostEqual(status["model_size_mb"], 2.0, places=1)
            self.assertEqual(status["scripture_embeddings_count"], 1)
            self.assertEqual(status["user_library_embeddings_count"], 1)

    def test_model_download_checksum_failure_cleans_up(self) -> None:
        mgr = NeuralModelManager(models_dir=self.models_dir)

        # Mock urlopen to return corrupt data that does not match expected sha
        fake_resp = io.BytesIO(b"corrupt-data-payload")
        with patch("search.ui.neural_manager.get_data_dir", return_value=self.data_dir), \
             patch("urllib.request.urlopen", return_value=fake_resp):
            mgr._run_download_worker()

        progress = mgr.get_download_progress()
        self.assertFalse(progress["in_progress"])
        self.assertIsNotNone(progress["error"])
        self.assertIn("Cryptographic hash mismatch", progress["error"])
        # Ensure no residual .tmp file remains
        tmp_files = list(self.data_dir.glob("**/*.tmp"))
        self.assertEqual(tmp_files, [])

    def test_model_download_already_installed(self) -> None:
        mgr = NeuralModelManager(models_dir=self.models_dir)
        with patch.object(mgr, "is_model_available", return_value=True):
            res = mgr.start_model_download()
            self.assertEqual(res["status"], "already_installed")

    def test_library_vectorization_without_model_raises(self) -> None:
        mgr = NeuralModelManager(models_dir=self.models_dir)
        with patch.object(mgr, "is_model_available", return_value=False):
            with self.assertRaises(RuntimeError):
                mgr.start_library_vectorization()

    def test_library_vectorization_worker(self) -> None:
        lib_db = self.data_dir / "library_embeddings.db"
        egw_db_path = self.data_dir / "egw.db"

        # Create mock egw.db
        conn = sqlite3.connect(egw_db_path)
        conn.execute("""
            CREATE TABLE egw_paragraphs (
                id TEXT PRIMARY KEY,
                book_code TEXT,
                book_title TEXT,
                chapter_title TEXT,
                text TEXT
            )
        """)
        conn.execute("INSERT INTO egw_paragraphs VALUES ('p1', 'PP', 'Patriarchs and Prophets', 'Creation', 'God created heavens.')")
        conn.execute("INSERT INTO egw_paragraphs VALUES ('p2', 'PP', 'Patriarchs and Prophets', 'Creation', 'The earth was empty.')")
        conn.commit()
        conn.close()

        mock_egw = MagicMock()
        mock_egw.exists.return_value = True
        mock_egw.db_path = egw_db_path

        mock_study = MagicMock()
        mock_study.egw_db = mock_egw

        mgr = NeuralModelManager(study_service=mock_study, models_dir=self.models_dir)

        # Mock OnnxEmbedder
        mock_embedder_instance = MagicMock()
        mock_embedder_instance.available.return_value = True
        mock_embedder_instance.model_name = "test-model"
        mock_embedder_instance.dim = 4
        mock_embedder_instance.embed_batch.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
        ], dtype=np.float32)

        with patch("search.ui.neural_manager.get_library_embeddings_db_path", return_value=lib_db), \
             patch("search.ui.neural_manager.OnnxEmbedder", return_value=mock_embedder_instance):
            mgr._run_vectorize_worker(batch_size=2, force=False)

        # Verify library_embeddings.db contents
        self.assertTrue(lib_db.is_file())
        conn_check = sqlite3.connect(lib_db)
        cur = conn_check.cursor()
        cur.execute("SELECT paragraph_id, book_code, magnitude FROM paragraphs ORDER BY paragraph_id")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "p1")
        self.assertEqual(rows[0][1], "PP")
        self.assertGreater(rows[0][2], 0.0)
        self.assertEqual(rows[1][0], "p2")

        cur.execute("SELECT value FROM meta WHERE key = 'total_paragraphs'")
        row_meta = cur.fetchone()
        self.assertEqual(row_meta[0], "2")
        conn_check.close()

        prog = mgr.get_vectorize_progress()
        self.assertFalse(prog["is_running"])
        self.assertEqual(prog["percent"], 100.0)
        self.assertIsNone(prog["error"])


class NeuralApiIntegrationTests(unittest.TestCase):
    """Integration tests testing HTTP REST endpoints for model and vector management."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.study = StudyService()
        cls.server = web_server.create_server(cls.study, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, _port = cls.server.server_address
        cls.base = f"http://{host}:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.study.close()

    def _get_json(self, path: str) -> dict:
        with urllib.request.urlopen(self.base + path, timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("application/json", res.headers.get_content_type())
            return json.loads(res.read())

    def _post_json(self, path: str, data: dict | None = None) -> tuple[int, dict]:
        body = json.dumps(data or {}).encode("utf-8") if data else b""
        req = urllib.request.Request(self.base + path, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                content = json.loads(res.read())
                return res.status, content
        except urllib.error.HTTPError as exc:
            content = json.loads(exc.read())
            return exc.code, content

    def test_health_advertises_neural_urls(self) -> None:
        payload = self._get_json("/api/health")
        self.assertEqual(payload.get("status"), "ok")
        self.assertEqual(payload.get("model_status_url"), "/api/model/status")
        self.assertEqual(payload.get("model_download_url"), "/api/model/download")
        self.assertEqual(payload.get("library_vectorize_url"), "/api/library/vectorize")

    def test_model_status_endpoint(self) -> None:
        status = self._get_json("/api/model/status")
        self.assertEqual(status.get("status"), "ok")
        self.assertIn("model_available", status)
        self.assertIn("model_name", status)
        self.assertIn("model_size_mb", status)
        self.assertIn("download_in_progress", status)
        self.assertIn("download_percent", status)
        self.assertIn("scripture_embeddings_count", status)
        self.assertIn("user_library_embeddings_count", status)

    def test_model_download_progress_endpoint(self) -> None:
        prog = self._get_json("/api/model/download/progress")
        self.assertEqual(prog.get("status"), "ok")
        self.assertIn("in_progress", prog)
        self.assertIn("percent", prog)

    def test_library_vectorize_progress_endpoint(self) -> None:
        prog = self._get_json("/api/library/vectorize/progress")
        self.assertEqual(prog.get("status"), "ok")
        self.assertIn("is_running", prog)
        self.assertIn("percent", prog)
        self.assertIn("eta_seconds", prog)

    def test_model_download_post_endpoint(self) -> None:
        code, res = self._post_json("/api/model/download")
        self.assertEqual(code, 200)
        self.assertIn(res.get("status"), ("already_installed", "started", "already_in_progress"))

    def test_library_vectorize_without_model_rejects(self) -> None:
        # If model is not installed, it should reject with HTTP 400
        with patch.object(self.study.neural_manager, "is_model_available", return_value=False):
            code, res = self._post_json("/api/library/vectorize")
            self.assertEqual(code, 400)
            self.assertIn("not installed", res.get("error", ""))


if __name__ == "__main__":
    unittest.main()
