"""Spirit of Prophecy (EGW) bulk ingestion engine & multi-format parsers.

Supports high-performance ingestion of Ellen G. White writings into the local
SQLite FTS5 database (data/egw.db) per ADR-0011 and ADR-0013.

Supported formats:
  1. Plain Text / Markdown (.txt, .md) with inline tokens ({PP 57.1}) or page breaks ([Page 57]).
  2. EPUB archives (.epub) with standard XHTML paragraphs and page-break anchors.
  3. JSON files (.json) with array of paragraph objects.
  4. Directory batching: auto-detects and ingests all supported formats in a folder.
  5. Public-domain harvester: downloads and ingests verified pre-1929 public-domain editions.

Zero external dependencies: uses Python standard library (zipfile, xml.etree, html.parser, urllib).
"""

from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
import zipfile
from typing import Any, Generator, Iterable

from search.linking.egw import (
    KNOWN_EGW_BOOKS,
    _TRIGGERS,
    EgwDB,
    normalize_token,
)

# Canonical verification anchors (token -> expected text start)
# Used to verify whether ingested editions match canonical pagination without blocking.
CANONICAL_ANCHORS: dict[str, dict[str, Any]] = {
    "PP.44.1": {
        "book_code": "PP",
        "text_start": "The earth came forth from the hand of its Maker surpassing lovely",
    },
    "PP.57.1": {
        "book_code": "PP",
        "text_start": "They heard the voice of the Lord God walking in the garden in the cool of the day",
    },
    "PP.66.1": {
        "book_code": "PP",
        "text_start": "To man the first intimation of redemption was communicated in the sentence",
    },
    "DA.19.1": {
        "book_code": "DA",
        "text_start": "His name shall be called Emmanuel, God with us",
    },
    "GC.582.1": {
        "book_code": "GC",
        "text_start": "From the very beginning of the great controversy in heaven it has been Satan",
    },
    "SC.9.1": {
        "book_code": "SC",
        "text_start": "Nature and revelation alike testify of God",
    },
    "SC.15.1": {
        "book_code": "SC",
        "text_start": "It was possible for Adam, before the fall, to form a righteous character",
    },
    "ED.13.1": {
        "book_code": "ED",
        "text_start": "True education means more than the pursual of a certain course of study",
    },
}


def normalize_for_hash(text: str) -> str:
    """Normalize text for invariant comparison across editions and typography."""
    norm = re.sub(r"[’']", "'", text.lower())
    norm = re.sub(r'["“”]', '"', norm)
    norm = re.sub(r"[—–\-]", " ", norm)
    norm = re.sub(r"[^\w\s]", "", norm)
    return re.sub(r"\s+", " ", norm).strip()


def compute_text_hash(text: str) -> str:
    """Compute deterministic SHA-256 of normalized text."""
    norm = normalize_for_hash(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def verify_book_anchors(db: EgwDB, book_code: str | None = None) -> list[dict[str, Any]]:
    """Verify local paragraphs against canonical checkpoint anchors.

    Returns a list of check results per anchor:
      {
        "token": "PP.57.1",
        "book_code": "PP",
        "status": "match" | "mismatch" | "missing",
        "message": "...",
      }
    Does NOT block ingestion; provides clear diagnostic warnings for edition discrepancies.
    """
    target_books = {book_code.upper()} if book_code else None
    results = []

    for token, spec in CANONICAL_ANCHORS.items():
        b = spec["book_code"]
        if target_books and b not in target_books:
            continue

        row = db.get_paragraph(token)
        if not row:
            results.append({
                "token": token,
                "book_code": b,
                "status": "missing",
                "message": f"Anchor paragraph {token} not present in local database.",
            })
            continue

        local_text = row["text"]
        norm_local = normalize_for_hash(local_text)
        norm_expected = normalize_for_hash(spec["text_start"])

        if norm_expected in norm_local:
            results.append({
                "token": token,
                "book_code": b,
                "status": "match",
                "message": f"Paragraph {token} matches canonical edition text.",
            })
        else:
            snippet = local_text[:80] + "..." if len(local_text) > 80 else local_text
            results.append({
                "token": token,
                "book_code": b,
                "status": "mismatch",
                "expected": spec["text_start"],
                "found": snippet,
                "message": (
                    f"Anchor mismatch on {token}. Expected text starting with '{spec['text_start'][:50]}...', "
                    f"but found '{snippet}'. Your copy may have non-standard pagination or be a different edition."
                ),
            })

    return results

# Standard citation token in text: {PP 57.1}, [PP 57.1], {57.1}, (PP 57.1)
_INLINE_TOKEN_RE = re.compile(
    r"[\{\[\(](?:egw:)?(?=[0-9A-Za-z]*[A-Za-z])([A-Za-z0-9]+)\s+([0-9]+)\.([0-9]+)[\}\]\)]",
    re.IGNORECASE,
)

# Explicit page marker: [Page 57], Page 57, [p. 57], --- 57 ---
_PAGE_MARKER_RE = re.compile(
    r"^(?:\[(?:Page|p\.)\s*([0-9]+)\]|Page\s+([0-9]+)|---\s*([0-9]+)\s*---)\s*$",
    re.IGNORECASE,
)

# Chapter heading: Chapter 1: The Creation, CHAPTER I.
_CHAPTER_HEADING_RE = re.compile(
    r"^(?:#+\s*)?(?:Chapter|CHAPTER)\s+([0-9IVXLCDM]+)(?:[:.\-–—]\s*(.*))?$",
    re.IGNORECASE,
)

# Roman numeral conversion
_ROMAN_MAP = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def parse_roman(numeral: str) -> int | None:
    """Parse Roman numeral into integer if valid, else None."""
    s = numeral.strip().upper()
    if not all(c in _ROMAN_MAP for c in s):
        return None
    total = 0
    prev_val = 0
    for c in reversed(s):
        val = _ROMAN_MAP[c]
        if val < prev_val:
            total -= val
        else:
            total += val
            prev_val = val
    return total if total > 0 else None


def detect_book_code(name_or_text: str) -> str | None:
    """Detect canonical EGW book code from file name, title, or initial text."""
    s = name_or_text.strip()
    upper = s.upper()

    # Exact book code match (e.g. "PP", "DA", "GC")
    for code in KNOWN_EGW_BOOKS:
        if upper == code:
            return code

    # Check filename stem or prefixes (e.g., "PP.txt", "DA_1898.epub")
    stem = Path(s).stem.upper()
    if stem in KNOWN_EGW_BOOKS:
        return stem
    for code in KNOWN_EGW_BOOKS:
        if stem.startswith(f"{code}_") or stem.startswith(f"{code}-") or stem.startswith(f"{code} "):
            return code

    # Match by full title substring
    for code, title in KNOWN_EGW_BOOKS.items():
        if title.lower() in s.lower():
            return code

    return None


class TextParagraphParser:
    """Parses plain text or Markdown files into structured EGW paragraph records."""

    def __init__(self, default_book_code: str | None = None):
        self.default_book_code = default_book_code.upper() if default_book_code else None

    def parse(self, text: str, filename_hint: str | None = None) -> list[dict[str, Any]]:
        """Parse text content into paragraph objects."""
        book_code = self.default_book_code
        if not book_code and filename_hint:
            book_code = detect_book_code(filename_hint)

        # Strip Project Gutenberg header and footer banners if present
        clean_text = text
        start_match = re.search(r"\*\*\*\s*START OF TH(?:E|IS) PROJECT GUTENBERG[^\n]*\*\*\*", clean_text, re.IGNORECASE)
        if start_match:
            clean_text = clean_text[start_match.end():]
        end_match = re.search(r"\*\*\*\s*END OF TH(?:E|IS) PROJECT GUTENBERG", clean_text, re.IGNORECASE)
        if end_match:
            clean_text = clean_text[:end_match.start()]

        lines = [line.strip() for line in clean_text.splitlines()]
        paragraphs: list[dict[str, Any]] = []

        curr_book = book_code or "EGW"
        curr_page = 1
        curr_para = 0
        curr_chap_num: int | None = None
        curr_chap_title: str | None = None

        # Buffer for accumulating multi-line paragraphs
        accum_lines: list[str] = []
        pending_override: tuple[str, int, int] | None = None

        def _flush_accum():
            nonlocal curr_para, pending_override
            if not accum_lines:
                return
            p_text = " ".join(accum_lines).strip()
            accum_lines.clear()
            if not p_text:
                return

            if pending_override:
                b, pg, pr = pending_override
                pending_override = None
            else:
                curr_para += 1
                b, pg, pr = curr_book, curr_page, curr_para

            paragraphs.append({
                "book_code": b,
                "book_title": KNOWN_EGW_BOOKS.get(b, b),
                "page": pg,
                "paragraph": pr,
                "chapter_num": curr_chap_num,
                "chapter_title": curr_chap_title,
                "text": p_text,
            })

        for line in lines:
            if not line:
                _flush_accum()
                continue

            # Check for chapter heading
            ch_match = _CHAPTER_HEADING_RE.match(line)
            if ch_match:
                _flush_accum()
                num_str = ch_match.group(1)
                curr_chap_num = int(num_str) if num_str.isdigit() else parse_roman(num_str)
                curr_chap_title = (ch_match.group(2) or "").strip() or None
                continue

            # Check for explicit page break marker
            pg_match = _PAGE_MARKER_RE.match(line)
            if pg_match:
                _flush_accum()
                val = pg_match.group(1) or pg_match.group(2) or pg_match.group(3)
                curr_page = int(val)
                curr_para = 0
                continue

            # Check for inline citation tokens at start of paragraph: {PP 57.1}
            tok_match = _INLINE_TOKEN_RE.search(line)
            if tok_match and tok_match.start() == 0:
                _flush_accum()
                b = tok_match.group(1).upper()
                pg = int(tok_match.group(2))
                pr = int(tok_match.group(3))
                curr_book = b
                curr_page = pg
                curr_para = pr
                pending_override = (b, pg, pr)
                # Remove token from text
                rem_text = line[tok_match.end():].strip()
                if rem_text:
                    accum_lines.append(rem_text)
                continue

            accum_lines.append(line)

        _flush_accum()
        return paragraphs


class _HtmlParagraphExtractor(HTMLParser):
    """Zero-dependency HTML/XHTML parser for EPUB chapter files."""

    def __init__(self):
        super().__init__()
        self.paragraphs: list[dict[str, Any]] = []
        self.current_page: int = 1
        self.current_para: int = 0
        self.current_chap_title: str | None = None
        self._in_p = False
        self._in_heading = False
        self._heading_buffer: list[str] = []
        self._text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr_dict = {k.lower(): v for k, v in attrs if v is not None}
        tag_lower = tag.lower()

        # Check for explicit page break anchors: <span id="page_57"/>, <a id="p.57"/>, <span id="pb_57"/>
        id_val = attr_dict.get("id") or attr_dict.get("name") or ""
        class_val = attr_dict.get("class") or ""

        page_match = re.search(r"(?:page[_\-]?|pb[_\-]|p\.)([0-9]+)", id_val, re.IGNORECASE)
        if page_match:
            self.current_page = int(page_match.group(1))
            self.current_para = 0

        if tag_lower in ("h1", "h2", "h3"):
            self._in_heading = True
            self._heading_buffer = []
        elif tag_lower in ("p", "div") and not self._in_p:
            self._in_p = True
            self._text_buffer = []

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in ("h1", "h2", "h3") and self._in_heading:
            self._in_heading = False
            heading_text = " ".join(self._heading_buffer).strip()
            if heading_text:
                self.current_chap_title = heading_text
        elif tag_lower in ("p", "div") and self._in_p:
            self._in_p = False
            p_text = html.unescape(" ".join(self._text_buffer)).strip()
            if p_text:
                # Check for inline citation tokens at the beginning of paragraph: {PP 57.1}
                tok_match = _INLINE_TOKEN_RE.search(p_text)
                if tok_match and tok_match.start() == 0:
                    b = tok_match.group(1).upper()
                    pg = int(tok_match.group(2))
                    pr = int(tok_match.group(3))
                    clean_text = _INLINE_TOKEN_RE.sub("", p_text).strip()
                    self.paragraphs.append({
                        "book_code": b,
                        "page": pg,
                        "paragraph": pr,
                        "chapter_title": self.current_chap_title,
                        "text": clean_text or p_text,
                    })
                    self.current_page = pg
                    self.current_para = pr
                else:
                    self.current_para += 1
                    self.paragraphs.append({
                        "page": self.current_page,
                        "paragraph": self.current_para,
                        "chapter_title": self.current_chap_title,
                        "text": p_text,
                    })

    def handle_data(self, data: str):
        clean = data.strip()
        if not clean:
            return
        if self._in_heading:
            self._heading_buffer.append(clean)
        elif self._in_p:
            self._text_buffer.append(clean)


class EpubParser:
    """Zero-dependency EPUB parser extracting book chapters and paragraphs."""

    def __init__(self, default_book_code: str | None = None):
        self.default_book_code = default_book_code.upper() if default_book_code else None

    def parse(self, epub_path: str | Path) -> list[dict[str, Any]]:
        path = Path(epub_path)
        if not path.is_file():
            raise FileNotFoundError(f"EPUB file not found: {path}")

        book_code = self.default_book_code or detect_book_code(path.name) or "EGW"
        book_title = KNOWN_EGW_BOOKS.get(book_code, book_code)

        paragraphs: list[dict[str, Any]] = []

        with zipfile.ZipFile(path, "r") as zf:
            # Locate OPF package file via META-INF/container.xml
            try:
                container_data = zf.read("META-INF/container.xml").decode("utf-8")
                opf_match = re.search(r'full-path="([^"]+)"', container_data)
                opf_path = opf_match.group(1) if opf_match else "content.opf"
            except KeyError:
                opf_path = "content.opf"

            opf_dir = str(Path(opf_path).parent)
            if opf_dir == ".":
                opf_dir = ""

            try:
                opf_content = zf.read(opf_path).decode("utf-8", errors="replace")
            except KeyError:
                # Fallback: find any .opf file in the archive
                opf_files = [n for n in zf.namelist() if n.endswith(".opf")]
                if not opf_files:
                    raise ValueError(f"Invalid EPUB archive: missing .opf package manifest in {path}")
                opf_path = opf_files[0]
                opf_dir = str(Path(opf_path).parent) if str(Path(opf_path).parent) != "." else ""
                opf_content = zf.read(opf_path).decode("utf-8", errors="replace")

            # Extract title if book_title is generic
            title_match = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", opf_content, re.IGNORECASE)
            if title_match:
                extracted_title = title_match.group(1).strip()
                if book_code == "EGW":
                    detected = detect_book_code(extracted_title)
                    if detected:
                        book_code = detected
                        book_title = KNOWN_EGW_BOOKS.get(book_code, extracted_title)
                    else:
                        book_title = extracted_title

            # Parse manifest items: id -> href
            manifest_items: dict[str, str] = {}
            for item in re.finditer(r'<item\b([^>]+)/?>', opf_content):
                attrs = dict(re.findall(r'(\w+)="([^"]+)"', item.group(1)))
                if "id" in attrs and "href" in attrs:
                    manifest_items[attrs["id"]] = attrs["href"]

            # Parse spine reading order: <itemref idref="..."/>
            spine_ids: list[str] = []
            for itemref in re.finditer(r'<itemref\b([^>]+)/?>', opf_content):
                attrs = dict(re.findall(r'(\w+)="([^"]+)"', itemref.group(1)))
                if "idref" in attrs:
                    spine_ids.append(attrs["idref"])

            # Read chapters in spine order
            chapter_files: list[str] = []
            for item_id in spine_ids:
                href = manifest_items.get(item_id)
                if href:
                    full_href = f"{opf_dir}/{href}" if opf_dir else href
                    # Normalize path for zipfile (always forward slashes)
                    norm = Path(full_href).as_posix()
                    if norm in zf.namelist():
                        chapter_files.append(norm)

            # Fallback if spine was empty: find all html/xhtml files
            if not chapter_files:
                chapter_files = sorted([n for n in zf.namelist() if n.endswith((".xhtml", ".html", ".htm"))])

            global_page = 1
            curr_para = 0
            for chap_idx, chap_file in enumerate(chapter_files, 1):
                try:
                    chap_html = zf.read(chap_file).decode("utf-8", errors="replace")
                except Exception:
                    continue

                parser = _HtmlParagraphExtractor()
                parser.current_page = global_page
                parser.current_para = curr_para
                parser.feed(chap_html)

                for p in parser.paragraphs:
                    b = p.get("book_code") or book_code
                    pg = p.get("page") or global_page
                    pr = p.get("paragraph", 1)
                    paragraphs.append({
                        "book_code": b,
                        "book_title": KNOWN_EGW_BOOKS.get(b, book_title),
                        "chapter_num": chap_idx,
                        "chapter_title": p.get("chapter_title"),
                        "page": pg,
                        "paragraph": pr,
                        "text": p["text"],
                    })

                if parser.paragraphs:
                    global_page = max(global_page, parser.current_page)
                    curr_para = parser.current_para

        return paragraphs


class BulkImporter:
    """Unified importer managing high-speed ingestion across multiple formats."""

    def __init__(self, db: EgwDB):
        self.db = db

    def import_file(self, file_path: str | Path, book_code: str | None = None, fast: bool = True) -> int:
        """Import an EPUB, TXT, MD, or JSON file."""
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")

        ext = p.suffix.lower()
        paragraphs: list[dict[str, Any]] = []

        if ext == ".epub":
            parser = EpubParser(default_book_code=book_code)
            paragraphs = parser.parse(p)
        elif ext in (".txt", ".md"):
            parser = TextParagraphParser(default_book_code=book_code)
            paragraphs = parser.parse(p.read_text(encoding="utf-8", errors="replace"), filename_hint=p.name)
        elif ext == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "paragraphs" in data:
                data = data["paragraphs"]
            if not isinstance(data, list):
                raise ValueError("JSON file must contain an array of paragraph objects.")
            paragraphs = data
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: .epub, .txt, .md, .json")

        if not paragraphs:
            return 0

        if fast:
            return self.db.fast_bulk_insert(paragraphs)
        return self.db.insert_paragraphs_batch(paragraphs)

    def import_directory(
        self,
        dir_path: str | Path,
        recursive: bool = True,
        fast: bool = True,
    ) -> dict[str, int]:
        """Scan and import all supported files (.epub, .txt, .md, .json) in a directory."""
        dir_p = Path(dir_path)
        if not dir_p.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_p}")

        pattern = "**/*" if recursive else "*"
        supported_exts = {".epub", ".txt", ".md", ".json"}

        # If fast mode is enabled, drop triggers once across the entire directory batch
        if fast:
            self.db.init_db()
            with self.db.conn:
                self.db.conn.execute("DROP TRIGGER IF EXISTS egw_ai;")
                self.db.conn.execute("DROP TRIGGER IF EXISTS egw_ad;")
                self.db.conn.execute("DROP TRIGGER IF EXISTS egw_au;")

        results: dict[str, int] = {}
        total_inserted = 0
        try:
            for file in sorted(dir_p.glob(pattern)):
                if file.is_file() and file.suffix.lower() in supported_exts:
                    rel_key = str(file.relative_to(dir_p))
                    try:
                        count = self.import_file(file, fast=False)
                        results[rel_key] = count
                        total_inserted += max(0, count)
                    except Exception:
                        results[rel_key] = -1
        finally:
            if fast:
                with self.db.conn:
                    self.db.conn.executescript(_TRIGGERS)
                    if total_inserted > 0:
                        self.db.conn.execute("INSERT INTO egw_fts(egw_fts) VALUES('rebuild');")

        return results


# Verified public-domain editions (pre-1929) available via public archives
PUBLIC_DOMAIN_SOURCES: dict[str, dict[str, str]] = {
    "GC": {
        "title": "The Great Controversy Between Christ and Satan",
        "url": "https://www.gutenberg.org/cache/epub/25833/pg25833.txt",
        "book_code": "GC",
    },
    "ED": {
        "title": "Education",
        "url": "https://www.gutenberg.org/cache/epub/62102/pg62102.txt",
        "book_code": "ED",
    },
}


def harvest_public_domain(
    work: str,
    db: EgwDB,
    dest_dir: str | Path = "data/egw-sources",
) -> int:
    """Download and ingest a verified public-domain EGW edition."""
    code = work.strip().upper()
    if code not in PUBLIC_DOMAIN_SOURCES:
        valid = ", ".join(PUBLIC_DOMAIN_SOURCES.keys())
        raise ValueError(f"Unknown public-domain work '{work}'. Available options: {valid}")

    spec = PUBLIC_DOMAIN_SOURCES[code]
    dest_path = Path(dest_dir) / f"{code}.txt"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Download if not already cached locally
    if not dest_path.is_file():
        req = urllib.request.Request(
            spec["url"],
            headers={"User-Agent": "AdventistBibleStudyTool/1.0 (offline research)"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())

    importer = BulkImporter(db)
    return importer.import_file(dest_path, book_code=code)
