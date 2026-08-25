"""Entry loading.

Loads Markdown entries (YAML frontmatter + body) and the curated semantic
links, normalizing them into plain dicts the pipeline can consume.

Uses PyYAML when available (it is a declared dependency) and otherwise
falls back to a conservative flat-list parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml

    _HAS_YAML = True
except Exception:  # pragma: no cover - fallback path
    _HAS_YAML = False


@dataclass
class Word:
    """A single lexical item (usually a Strong's-numbered word)."""

    strongs: str
    word: str = ""
    transliteration: str = ""
    definition: str = ""
    language: str = ""
    scripture_entries: list = field(default_factory=list)


@dataclass
class Entry:
    """A loaded knowledge-base entry."""

    id: str
    path: str
    frontmatter: dict
    body: str
    tags: list = field(default_factory=list)
    strongs: list = field(default_factory=list)
    passage: str = ""
    semantic_links: list = field(default_factory=list)
    words: list = field(default_factory=list)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) from a Markdown document.

    Supports two header conventions:
    * Standard YAML  ``---`` ... ``---``
    * MVP convention ``* * *`` then ``## key: value`` lines, ending at the
      first level-1 heading ``# Title`` (the body).
    """
    lines = content.split("\n")

    # Detect the opening delimiter.
    if content.startswith("---"):
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx is None:
            return {}, content
        fm_text = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1 :])
        if _HAS_YAML:
            try:
                return yaml.safe_load(fm_text) or {}, body
            except Exception:
                pass
        return _parse_frontmatter_simple(fm_text), body

    # MVP convention: block from '* * *' up to first '# ' heading.
    if content.lstrip().startswith("* * *"):
        start = 0
        for i, ln in enumerate(lines):
            if ln.strip() == "* * *":
                start = i + 1
                break
        end_idx = len(lines)
        for i in range(start, len(lines)):
            if lines[i].startswith("# "):
                end_idx = i
                break
        fm_text = "\n".join(lines[start:end_idx])
        # The MVP header uses '## key: value' — strip the leading '## '.
        fm_lines = []
        for ln in fm_text.split("\n"):
            s = ln.strip()
            if s.startswith("## "):
                s = s[3:]
            if s:
                fm_lines.append(s)
        fm_text = "\n".join(fm_lines)
        body = "\n".join(lines[end_idx + 1 :])
        if _HAS_YAML:
            try:
                return yaml.safe_load(fm_text) or {}, body
            except Exception:
                pass
        return _parse_frontmatter_simple(fm_text), body

    return {}, content


def _parse_frontmatter_simple(fm_text: str) -> dict:
    """Minimal YAML fallback: scalar keys and flat "- item" lists."""
    result: dict = {}
    cur_key = None
    cur_list: list = []
    for raw in fm_text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and cur_key is not None:
            cur_list.append(line[2:].strip().strip('"').strip("'"))
            continue
        if ":" in line:
            if cur_key is not None:
                result[cur_key] = cur_list if cur_list else result.get(cur_key)
                cur_list = []
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
            else:
                cur_key = key
    if cur_key is not None:
        result[cur_key] = cur_list if cur_list else result.get(cur_key)
    return result


_WORD_RE = re.compile(
    r"^#{3,4}\s+(?P<title>[^\n]+?)\s*-\s*Strong's\s+(?P<strongs>[HhGg]\d+)",
    re.MULTILINE,
)
_FIELD_RE = re.compile(r"^\*\s*(?P<key>transliteration|definition|language)\s*:\s*(?P<val>.*)", re.I | re.MULTILINE)


def _extract_words(body: str) -> list[dict]:
    """Pull Hebrew/Greek word-study blocks out of an entry body.

    Matches the convention used in the Genesis MVP entries:
      ### bara (to create) - Strong's H1254
      * Transliteration: bara
      * Definition: to create, shape, form
    """
    words: list[dict] = []
    for m in _WORD_RE.finditer(body):
        title = m.group("title").strip()
        # Strip a parenthetical transliteration: "bara (to create)" -> "bara"
        word = title.split("(")[0].strip()
        entry = {"strongs": m.group("strongs").upper(), "word": word}
        # Find the block until the next word-study header.
        block_start = m.end()
        next_m = _WORD_RE.search(body, block_start)
        block = body[block_start : next_m.start() if next_m else len(body)]
        for fm in _FIELD_RE.finditer(block):
            key = fm.group("key").lower().strip()
            val = fm.group("val").strip()
            if val:
                entry[key] = val
        words.append(entry)
    return words


def _list_field(fm: dict, key: str) -> list:
    val = fm.get(key, [])
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    return list(val)


class Loader:
    """Loads entries from the materials tree and curated semantic links."""

    def __init__(self, repo_root="."):
        self.repo_root = Path(repo_root)
        self.entries: list[Entry] = []

    def load_entries(self, materials_dir="materials") -> list:
        """Load all Markdown entries under materials/ and cache them."""
        materials_path = self.repo_root / materials_dir
        if not materials_path.exists():
            return []
        entries: list[Entry] = []
        for md_file in sorted(materials_path.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(content)
            if not fm:
                continue
            tags = _list_field(fm, "tags")
            strongs = [t for t in tags if t.startswith("strongs-")]
            entries.append(
                Entry(
                    id=fm.get("id", str(md_file)),
                    path=str(md_file.relative_to(self.repo_root)),
                    frontmatter=fm,
                    body=body,
                    tags=tags,
                    strongs=strongs,
                    passage=fm.get("passage", ""),
                    semantic_links=_list_field(fm, "semantic_links"),
                    words=_extract_words(body),
                )
            )
        self.entries = entries
        return entries

    def load_links(self, links_file="correlations/semantic-links.json") -> dict | None:
        links_path = self.repo_root / links_file
        if not links_path.exists():
            return None
        if not _HAS_YAML:
            return None
        with open(links_path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def index_by(self, key="id") -> dict:
        return {getattr(e, key): e for e in self.entries}
