"""Curation manifest generator and verifier (WP-037, Phase 2).

CLI usage
---------
    python -m search.corpus.curation_manifest --generate
    python -m search.corpus.curation_manifest --check

Design
------
* Scans every Markdown file under ``materials/bible/`` (recursively).
* Picks up entries whose frontmatter ``status`` equals ``approved``.
* For each approved entry, computes a **stable SHA-256** over the content with
  the mutable ``updated`` timestamp line stripped, so incidental re-saves of
  unrelated fields do not invalidate the manifest.
* Serialises to ``data/curation-manifest.json`` (sorted by entry-id, fully
  deterministic output).
* ``--check`` mode: re-derives hashes and fails fast if any approved entry has
  been tampered with or if any entry is newly approved but absent from the
  manifest.  This is wired into ``scripts/verify_all.sh``.

Fail-fast, never silent
-----------------------
Any structural anomaly (duplicate id, unreadable YAML, missing required field)
raises ``CurationManifestError`` rather than silently skipping the entry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyYAML is required: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parent.parent.parent
MATERIALS_DIR = ROOT / "materials" / "bible"
MANIFEST_PATH = ROOT / "data" / "curation-manifest.json"

# Lines matching these patterns are excluded from the stable hash so that
# incidental timestamp updates do not invalidate a sealed entry.
_MUTABLE_LINE_RE = re.compile(r"^updated:\s+", re.IGNORECASE)


class CurationManifestError(RuntimeError):
    """Raised on integrity failures or structural anomalies."""


# ---------------------------------------------------------------------------
# Stable content hash
# ---------------------------------------------------------------------------

def _stable_hash(path: Path) -> str:
    """Return SHA-256 of the file content with mutable frontmatter timestamp lines stripped."""
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm_lines = [l for l in parts[1].splitlines() if not _MUTABLE_LINE_RE.match(l)]
            stable = f"---{chr(10).join(fm_lines)}---{parts[2]}"
            return hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Frontmatter parsing (lightweight, no heavy dependency)
# ---------------------------------------------------------------------------

def _parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_text) or raise CurationManifestError."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise CurationManifestError(f"{path}: malformed YAML frontmatter (missing closing ---)")
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise CurationManifestError(f"{path}: invalid YAML frontmatter — {exc}") from exc
    return fm, parts[2]


# ---------------------------------------------------------------------------
# Entry dataclass
# ---------------------------------------------------------------------------

@dataclass
class ManifestEntry:
    """A single approved entry sealed into the curation manifest."""
    id: str
    path: str          # relative to repo root
    sha256: str        # stable content hash (updated field stripped)
    passage: str
    book: str
    status: str        # always "approved"
    approved_date: str | None = None
    reviewed_by: str | None = None
    doctrinal_framework: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_approved_entries(materials_dir: Path = MATERIALS_DIR) -> list[ManifestEntry]:
    """Scan materials/bible/ and return ManifestEntry for every approved file."""
    if not materials_dir.is_dir():
        raise CurationManifestError(f"Materials directory not found: {materials_dir}")

    entries: list[ManifestEntry] = []
    seen_ids: set[str] = set()

    for md_path in sorted(materials_dir.rglob("*.md")):
        fm, _ = _parse_frontmatter(md_path)
        status = str(fm.get("status", "")).strip()
        if status != "approved":
            continue

        entry_id = str(fm.get("id", "")).strip()
        if not entry_id:
            raise CurationManifestError(f"{md_path}: approved entry has no 'id' field")
        if entry_id in seen_ids:
            raise CurationManifestError(f"Duplicate entry id '{entry_id}' in {md_path}")
        seen_ids.add(entry_id)

        try:
            rel_path = str(md_path.relative_to(ROOT))
        except ValueError:
            # materials_dir is outside the repo root (e.g. test tmp directories).
            # Fall back to absolute path so the manifest records a usable location.
            rel_path = str(md_path)
        entries.append(ManifestEntry(
            id=entry_id,
            path=rel_path,
            sha256=_stable_hash(md_path),
            passage=str(fm.get("passage", "")).strip(),
            book=str(fm.get("book", "")).strip(),
            status="approved",
            approved_date=str(fm["approved_date"]) if "approved_date" in fm else None,
            reviewed_by=str(fm["reviewed_by"]) if "reviewed_by" in fm else None,
            doctrinal_framework=str(fm["doctrinal_framework"]) if "doctrinal_framework" in fm else None,
        ))

    return entries


# ---------------------------------------------------------------------------
# Serialise / deserialise manifest
# ---------------------------------------------------------------------------

_MANIFEST_SCHEMA = "curation-manifest/v1"


def generate_manifest(
    materials_dir: Path = MATERIALS_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    """Generate and write ``data/curation-manifest.json``. Returns the manifest dict."""
    entries = scan_approved_entries(materials_dir)
    manifest: dict[str, Any] = {
        "$schema": _MANIFEST_SCHEMA,
        "generated_by": "search.corpus.curation_manifest",
        "total_approved": len(entries),
        "entries": [e.to_dict() for e in entries],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load and return the manifest JSON, or raise if missing/malformed."""
    if not manifest_path.is_file():
        raise CurationManifestError(
            f"Curation manifest not found: {manifest_path}\n"
            "Run: python -m search.corpus.curation_manifest --generate"
        )
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CurationManifestError(f"Manifest is not valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Integrity check
# ---------------------------------------------------------------------------

def check_manifest(
    materials_dir: Path = MATERIALS_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> list[str]:
    """Return a list of failure messages (empty = clean).

    Checks:
    1. All entries in the manifest still exist on disk and hash correctly.
    2. No approved entry on disk is absent from the manifest (new approvals
       that were not re-generated are a silent integrity gap).
    """
    manifest = load_manifest(manifest_path)
    failures: list[str] = []

    # Build index from manifest
    pinned: dict[str, dict[str, Any]] = {
        e["id"]: e for e in manifest.get("entries", [])
    }

    # Check every pinned entry
    for entry_id, pinned_entry in pinned.items():
        pinned_path = pinned_entry["path"]
        # If stored path is absolute (happens when materials_dir is outside ROOT,
        # e.g. in tests), use it directly; otherwise resolve relative to ROOT.
        on_disk = Path(pinned_path) if Path(pinned_path).is_absolute() else ROOT / pinned_path
        if not on_disk.is_file():
            failures.append(
                f"MISSING  {entry_id}: pinned file no longer exists at {pinned_entry['path']}"
            )
            continue
        actual_hash = _stable_hash(on_disk)
        if actual_hash != pinned_entry["sha256"]:
            failures.append(
                f"TAMPERED {entry_id}: content hash mismatch\n"
                f"  expected {pinned_entry['sha256']}\n"
                f"  actual   {actual_hash}\n"
                f"  file     {pinned_entry['path']}\n"
                f"  Re-generate manifest: python -m search.corpus.curation_manifest --generate"
            )

    # Check for newly approved entries not yet in manifest
    live_entries = scan_approved_entries(materials_dir)
    for entry in live_entries:
        if entry.id not in pinned:
            failures.append(
                f"UNSEALED {entry.id}: approved on disk but absent from manifest\n"
                f"  file {entry.path}\n"
                f"  Re-generate manifest: python -m search.corpus.curation_manifest --generate"
            )

    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Curation manifest — generate or verify the cryptographic seal on approved entries.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--generate",
        action="store_true",
        help="Scan materials/bible/ and (re-)generate data/curation-manifest.json.",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Verify the manifest against the current working tree; exit 1 if any tampering is detected.",
    )
    args = parser.parse_args(argv)

    if args.generate:
        try:
            manifest = generate_manifest(materials_dir=MATERIALS_DIR, manifest_path=MANIFEST_PATH)
            n = manifest["total_approved"]
            print(f"✔ Curation manifest generated: {n} approved entr{'y' if n == 1 else 'ies'} sealed")
            print(f"  → {MANIFEST_PATH}")
        except CurationManifestError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0

    # --check
    try:
        failures = check_manifest(materials_dir=MATERIALS_DIR, manifest_path=MANIFEST_PATH)
    except CurationManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not failures:
        manifest = load_manifest(manifest_path=MANIFEST_PATH)
        n = manifest.get("total_approved", "?")
        print(f"✔ Curation manifest OK — {n} approved entr{'y' if n == 1 else 'ies'} verified")
        return 0

    print(f"✘ Curation manifest FAILED — {len(failures)} issue(s):", file=sys.stderr)
    for msg in failures:
        print(f"\n  {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
