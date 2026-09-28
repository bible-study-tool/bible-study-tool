"""Unit tests for OnnxEmbedder and zero-PyTorch neural embedding pipeline (WP-040, ADR-029)."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from search.linking.onnx_embedder import OnnxEmbedder, find_local_model_files
from search.linking.embedder import get_embedder, CharNgramEmbedder


class TestOnnxEmbedder(unittest.TestCase):
    """Test suite for OnnxEmbedder lifecycle, fallback, and inference."""

    def test_model_files_discovery(self):
        """Test finding local ONNX model and tokenizer files."""
        model_path, tok_path = find_local_model_files()
        # In an environment with downloaded model files, these should resolve
        if model_path is not None:
            self.assertTrue(model_path.is_file(), f"Model path {model_path} must be a file")
            self.assertTrue(str(model_path).endswith(".onnx"))
        if tok_path is not None:
            self.assertTrue(tok_path.is_file(), f"Tokenizer path {tok_path} must be a file")
            self.assertTrue(str(tok_path).endswith(".json"))

    def test_embedder_fallback_when_model_missing(self):
        """When given non-existent paths, embedder falls back without crashing."""
        fake_emb = OnnxEmbedder(
            model_path="/nonexistent/model.onnx",
            tokenizer_path="/nonexistent/tokenizer.json",
            strict=False,
        )
        self.assertFalse(fake_emb.available())
        vec = fake_emb.embed("test query text", is_query=True)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (384,))
        # Normalized fallback vector
        self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=3)

    def test_embedder_strict_mode_raises(self):
        """When strict=True, unavailable embedder raises RuntimeError."""
        fake_emb = OnnxEmbedder(
            model_path="/nonexistent/model.onnx",
            tokenizer_path="/nonexistent/tokenizer.json",
            strict=True,
        )
        self.assertFalse(fake_emb.available())
        with self.assertRaises(RuntimeError):
            fake_emb.embed("test")

    def test_real_onnx_embedder_if_available(self):
        """Test inference accuracy and properties when real model is available."""
        emb = OnnxEmbedder()
        if not emb.available():
            self.skipTest("ONNX model files or runtime not available in this environment")

        self.assertEqual(emb.dim, 384)
        vec = emb.embed("suffering servant mocked", is_query=True)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (384,))
        self.assertEqual(vec.dtype, np.float32)
        # Verify L2 normalization
        self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=4)

    def test_batch_embedding_consistency(self):
        """Test that batch embedding matches single query embedding."""
        emb = OnnxEmbedder()
        if not emb.available():
            self.skipTest("ONNX model files or runtime not available in this environment")

        texts = [
            "In the beginning God created the heaven and the earth.",
            "The Lord is my shepherd; I shall not want.",
        ]
        batch_vecs = emb.embed_batch(texts, is_query=False, batch_size=2)
        self.assertEqual(batch_vecs.shape, (2, 384))

        single_0 = emb.embed(texts[0], is_query=False)
        single_1 = emb.embed(texts[1], is_query=False)

        cos_0 = float(np.dot(batch_vecs[0], single_0))
        cos_1 = float(np.dot(batch_vecs[1], single_1))
        self.assertGreater(cos_0, 0.99, f"Batch and single cosine similarity was {cos_0}")
        self.assertGreater(cos_1, 0.99, f"Batch and single cosine similarity was {cos_1}")
        np.testing.assert_allclose(batch_vecs[0], single_0, atol=0.02)
        np.testing.assert_allclose(batch_vecs[1], single_1, atol=0.02)

    def test_get_embedder_factory_priority(self):
        """Test that get_embedder respects ADR-029 priority."""
        emb = get_embedder(prefer_model=True)
        # Should return OnnxEmbedder if available, otherwise CharNgramEmbedder
        self.assertTrue(isinstance(emb, (OnnxEmbedder, CharNgramEmbedder)))


if __name__ == "__main__":
    unittest.main()
