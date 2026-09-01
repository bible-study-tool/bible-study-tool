"""Shared test utilities.

The deterministic test suite splits into two tiers:

1. **Offline-safe tests** — read only committed artifacts (lexicons/,
   correlations/, materials/, tags/) plus data/PROVENANCE.md. These run on a
   fresh clone and in CI (raw sources are gitignored).
2. **Raw-source-dependent tests** — regeneration tripwires, corpus fidelity
   vs data/KJV-osis.json, morphology vs data/oshb/Gen.xml, the agreement
   adapters. These require `data/` (fetched via scripts/fetch_sources.sh).

This mirrors scripts/verify_all.sh, which already skips raw-source checks
when `data/` is absent ("a fresh clone skips this step automatically, and the
committed artifacts are still verified by the checksum gate"). The committed
artifacts remain guarded offline by the PROVENANCE checksum gate
(search/corpus/test_morphology.py::ProvenanceChecksumGateTests).
"""

from __future__ import annotations

import unittest
from pathlib import Path

# The two files every raw-source-dependent test needs. fetch_sources.sh
# guarantees both exist together, so checking these two is sufficient.
_REQUIRED_RAW_SOURCES = ("data/KJV-osis.json", "data/oshb/Gen.xml")


def raw_sources_present(repo: str = ".") -> bool:
    """True when the gitignored raw sources are available locally."""
    return all((Path(repo) / p).exists() for p in _REQUIRED_RAW_SOURCES)


def require_raw_sources() -> unittest.skipUnless:
    """Skip decorator for tests that need the gitignored raw sources.

    Usage on a class or a method::

        @require_raw_sources()
        class RegenerationTripwireTests(unittest.TestCase):
            ...
    """
    return unittest.skipUnless(
        raw_sources_present(),
        "raw sources not present (data/ is gitignored; run "
        "scripts/fetch_sources.sh to enable this test)",
    )