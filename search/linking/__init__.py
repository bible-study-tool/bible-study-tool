"""Semantic linking pipeline for the Bible Study Tool.

Two cooperating layers:

(b) Deterministic root concordance  -> search/linking/concordance.py
    Same-lexeme (Strong's) cross-passage links. Human-verified, offline.

(c) Multilingual semantic discovery -> search/linking/candidates.py
    Cross-language candidate links *beyond* Strong's, gated by strict
    rules and always written to ai-discovered-links.json for review.

The embedder (search/linking/embedder.py) is pluggable: it will use a real
multilingual sentence-transformer model when available and otherwise falls
back to a deterministic, offline, cross-script character n-gram embedder.
"""

from .loader import Loader
from .embedder import get_embedder
from .concordance import build_concordance
from .candidates import discover_candidates, GateKeeper
from .egw import (
    ALL_OFFICIAL_EGW_CODES,
    EgwDB,
    KNOWN_EGW_BOOKS,
    is_egw_token,
    normalize_token,
)
from .egw_importer import BulkImporter, EpubParser, TextParagraphParser

__all__ = [
    "Loader",
    "get_embedder",
    "build_concordance",
    "discover_candidates",
    "GateKeeper",
    "EgwDB",
    "KNOWN_EGW_BOOKS",
    "ALL_OFFICIAL_EGW_CODES",
    "is_egw_token",
    "normalize_token",
    "BulkImporter",
    "EpubParser",
    "TextParagraphParser",
]

