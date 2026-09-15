"""Tests for search.corpus.curation_manifest (WP-037, Phase 4).

Tests cover:
- Manifest generation from a controlled temp directory of sample entries.
- Correct exclusion of non-approved entries.
- Tampering detection (modified content with unchanged manifest raises).
- Newly approved entry absent from manifest detected by --check.
- Schema conformance of the generated JSON.
- CLI exit codes for --generate and --check modes.
- EGW token routing in action_tab_xrefs (from TUI fix in WP-036) is NOT
  tested here; see test_textual.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import textwrap
from pathlib import Path

import pytest

from search.corpus.curation_manifest import (
    CurationManifestError,
    _stable_hash,
    check_manifest,
    generate_manifest,
    load_manifest,
    scan_approved_entries,
    _cli,
    _MANIFEST_SCHEMA,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_entry(parent: Path, filename: str, frontmatter: dict, body: str = "Body text.") -> Path:
    """Write a minimal Markdown entry with YAML frontmatter."""
    import yaml as _yaml
    fm_str = _yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    path = parent / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm_str}\n---\n\n{body}\n", encoding="utf-8")
    return path


def _base_fm(entry_id: str, status: str = "approved") -> dict:
    return {
        "id": entry_id,
        "type": "material/bible",
        "book": "book/genesis",
        "passage": "Genesis 1:1",
        "source": "source/bible",
        "language": "hebrew",
        "tags": ["material/bible", "book/genesis"],
        "level": "intro",
        "status": status,
        "created": "2026-09-01",
        "updated": "2026-09-01",
    }


# ---------------------------------------------------------------------------
# stable hash
# ---------------------------------------------------------------------------

class TestStableHash:
    def test_deterministic(self, tmp_path: Path) -> None:
        p = tmp_path / "entry.md"
        p.write_text("---\nstatus: approved\n---\nBody.\n", encoding="utf-8")
        assert _stable_hash(p) == _stable_hash(p)

    def test_ignores_updated_line(self, tmp_path: Path) -> None:
        p1 = tmp_path / "a.md"
        p2 = tmp_path / "b.md"
        p1.write_text("---\nstatus: approved\nupdated: 2026-01-01\n---\nBody.\n", encoding="utf-8")
        p2.write_text("---\nstatus: approved\nupdated: 2026-12-31\n---\nBody.\n", encoding="utf-8")
        assert _stable_hash(p1) == _stable_hash(p2)

    def test_sensitive_to_body_change(self, tmp_path: Path) -> None:
        p1 = tmp_path / "a.md"
        p2 = tmp_path / "b.md"
        p1.write_text("---\nstatus: approved\n---\nOriginal body.\n", encoding="utf-8")
        p2.write_text("---\nstatus: approved\n---\nTampered body!\n", encoding="utf-8")
        assert _stable_hash(p1) != _stable_hash(p2)

    def test_sensitive_to_frontmatter_change(self, tmp_path: Path) -> None:
        p1 = tmp_path / "a.md"
        p2 = tmp_path / "b.md"
        p1.write_text("---\nstatus: approved\nid: gen-1-1\n---\nBody.\n", encoding="utf-8")
        p2.write_text("---\nstatus: approved\nid: gen-1-2\n---\nBody.\n", encoding="utf-8")
        assert _stable_hash(p1) != _stable_hash(p2)


# ---------------------------------------------------------------------------
# scan_approved_entries
# ---------------------------------------------------------------------------

class TestScanApprovedEntries:
    def test_picks_up_approved_entries(self, tmp_path: Path) -> None:
        _write_entry(tmp_path, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        _write_entry(tmp_path, "b.md", _base_fm("gen-1-2-kjv", "draft"))
        _write_entry(tmp_path, "c.md", _base_fm("gen-1-3-kjv", "review"))

        entries = scan_approved_entries(tmp_path)
        assert len(entries) == 1
        assert entries[0].id == "gen-1-1-kjv"
        assert entries[0].status == "approved"

    def test_empty_when_no_approved(self, tmp_path: Path) -> None:
        _write_entry(tmp_path, "a.md", _base_fm("gen-1-1", "draft"))
        assert scan_approved_entries(tmp_path) == []

    def test_raises_on_duplicate_id(self, tmp_path: Path) -> None:
        _write_entry(tmp_path, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        _write_entry(tmp_path, "b.md", _base_fm("gen-1-1-kjv", "approved"))
        with pytest.raises(CurationManifestError, match="Duplicate entry id"):
            scan_approved_entries(tmp_path)

    def test_raises_on_missing_id(self, tmp_path: Path) -> None:
        fm = _base_fm("", "approved")
        fm.pop("id")
        _write_entry(tmp_path, "a.md", fm)
        with pytest.raises(CurationManifestError, match="no 'id' field"):
            scan_approved_entries(tmp_path)

    def test_raises_on_missing_materials_dir(self, tmp_path: Path) -> None:
        with pytest.raises(CurationManifestError, match="not found"):
            scan_approved_entries(tmp_path / "nonexistent")

    def test_optional_review_metadata(self, tmp_path: Path) -> None:
        fm = _base_fm("gen-1-1-kjv", "approved")
        fm["reviewed_by"] = "reviewer-a"
        fm["approved_date"] = "2026-09-15"
        fm["doctrinal_framework"] = "SDA Historicist"
        _write_entry(tmp_path, "a.md", fm)

        entries = scan_approved_entries(tmp_path)
        assert len(entries) == 1
        e = entries[0]
        assert e.reviewed_by == "reviewer-a"
        assert e.approved_date == "2026-09-15"
        assert e.doctrinal_framework == "SDA Historicist"


# ---------------------------------------------------------------------------
# generate_manifest
# ---------------------------------------------------------------------------

class TestGenerateManifest:
    def test_generates_json_file(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        _write_entry(materials, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        manifest_path = tmp_path / "manifest.json"

        result = generate_manifest(materials_dir=materials, manifest_path=manifest_path)

        assert manifest_path.is_file()
        assert result["$schema"] == _MANIFEST_SCHEMA
        assert result["total_approved"] == 1
        assert result["entries"][0]["id"] == "gen-1-1-kjv"

    def test_zero_entries_when_none_approved(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        _write_entry(materials, "a.md", _base_fm("gen-1-1", "draft"))
        manifest_path = tmp_path / "manifest.json"

        result = generate_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert result["total_approved"] == 0
        assert result["entries"] == []

    def test_manifest_is_valid_json(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        _write_entry(materials, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        manifest_path = tmp_path / "manifest.json"

        generate_manifest(materials_dir=materials, manifest_path=manifest_path)
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        assert "$schema" in loaded

    def test_manifest_entries_sorted_by_id(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        _write_entry(materials, "z.md", {**_base_fm("gen-1-3-kjv", "approved"), "passage": "Genesis 1:3"})
        _write_entry(materials, "a.md", {**_base_fm("gen-1-1-kjv", "approved"), "passage": "Genesis 1:1"})
        _write_entry(materials, "m.md", {**_base_fm("gen-1-2-kjv", "approved"), "passage": "Genesis 1:2"})
        manifest_path = tmp_path / "manifest.json"

        result = generate_manifest(materials_dir=materials, manifest_path=manifest_path)
        ids = [e["id"] for e in result["entries"]]
        assert ids == sorted(ids)

    def test_sha256_recorded(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        p = _write_entry(materials, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        manifest_path = tmp_path / "manifest.json"

        result = generate_manifest(materials_dir=materials, manifest_path=manifest_path)
        entry = result["entries"][0]
        assert re.match(r"^[0-9a-f]{64}$", entry["sha256"])
        assert entry["sha256"] == _stable_hash(p)


# ---------------------------------------------------------------------------
# check_manifest (tampering detection)
# ---------------------------------------------------------------------------

class TestCheckManifest:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        materials = tmp_path / "materials" / "bible"
        manifest_path = tmp_path / "manifest.json"
        p = _write_entry(materials, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        generate_manifest(materials_dir=materials, manifest_path=manifest_path)
        return materials, manifest_path, p

    def test_clean_state_passes(self, tmp_path: Path) -> None:
        materials, manifest_path, _ = self._setup(tmp_path)
        failures = check_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert failures == []

    def test_detects_tampered_body(self, tmp_path: Path) -> None:
        materials, manifest_path, entry_path = self._setup(tmp_path)
        original = entry_path.read_text(encoding="utf-8")
        entry_path.write_text(original + "\nTAMPERED: injected content\n", encoding="utf-8")

        failures = check_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert len(failures) == 1
        assert "TAMPERED" in failures[0]
        assert "gen-1-1-kjv" in failures[0]

    def test_detects_deleted_pinned_file(self, tmp_path: Path) -> None:
        materials, manifest_path, entry_path = self._setup(tmp_path)
        entry_path.unlink()

        failures = check_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert len(failures) == 1
        assert "MISSING" in failures[0]

    def test_detects_newly_approved_absent_from_manifest(self, tmp_path: Path) -> None:
        materials, manifest_path, _ = self._setup(tmp_path)
        # Add a new approved entry without regenerating the manifest
        _write_entry(materials, "b.md", {**_base_fm("gen-1-2-kjv", "approved"), "passage": "Genesis 1:2"})

        failures = check_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert len(failures) == 1
        assert "UNSEALED" in failures[0]
        assert "gen-1-2-kjv" in failures[0]

    def test_ignores_updated_timestamp_change(self, tmp_path: Path) -> None:
        materials, manifest_path, entry_path = self._setup(tmp_path)
        original = entry_path.read_text(encoding="utf-8")
        # Replace the updated date — should NOT be detected as tampering
        modified = re.sub(r"updated: \S+", "updated: 2099-01-01", original)
        entry_path.write_text(modified, encoding="utf-8")

        failures = check_manifest(materials_dir=materials, manifest_path=manifest_path)
        assert failures == []

    def test_raises_if_manifest_missing(self, tmp_path: Path) -> None:
        materials = tmp_path / "materials" / "bible"
        materials.mkdir(parents=True)
        with pytest.raises(CurationManifestError, match="not found"):
            check_manifest(materials_dir=materials, manifest_path=tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_generate_exits_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import search.corpus.curation_manifest as cm
        monkeypatch.setattr(cm, "MATERIALS_DIR", tmp_path / "materials" / "bible")
        monkeypatch.setattr(cm, "MANIFEST_PATH", tmp_path / "manifest.json")
        (tmp_path / "materials" / "bible").mkdir(parents=True)
        assert _cli(["--generate"]) == 0

    def test_check_exits_zero_when_clean(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import search.corpus.curation_manifest as cm
        materials = tmp_path / "materials" / "bible"
        manifest_path = tmp_path / "manifest.json"
        monkeypatch.setattr(cm, "MATERIALS_DIR", materials)
        monkeypatch.setattr(cm, "MANIFEST_PATH", manifest_path)
        materials.mkdir(parents=True)
        _cli(["--generate"])
        assert _cli(["--check"]) == 0

    def test_check_exits_one_on_tampering(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import search.corpus.curation_manifest as cm
        materials = tmp_path / "materials" / "bible"
        manifest_path = tmp_path / "manifest.json"
        monkeypatch.setattr(cm, "MATERIALS_DIR", materials)
        monkeypatch.setattr(cm, "MANIFEST_PATH", manifest_path)
        _write_entry(materials, "a.md", _base_fm("gen-1-1-kjv", "approved"))
        _cli(["--generate"])

        # Tamper with the entry
        entry_path = materials / "a.md"
        entry_path.write_text(entry_path.read_text() + "\nMalicious line\n")
        assert _cli(["--check"]) == 1

    def test_check_exits_one_when_manifest_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import search.corpus.curation_manifest as cm
        monkeypatch.setattr(cm, "MATERIALS_DIR", tmp_path / "materials" / "bible")
        monkeypatch.setattr(cm, "MANIFEST_PATH", tmp_path / "nonexistent.json")
        (tmp_path / "materials" / "bible").mkdir(parents=True)
        assert _cli(["--check"]) == 1
