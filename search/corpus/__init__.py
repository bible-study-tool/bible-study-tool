"""Content-package: deterministic corpus builders for the knowledge base.

Everything here generates entry Markdown strictly from PINNED source data
(see data/PROVENANCE.md). No interpretive content (theological notes,
cross-references) is ever generated — that is human-curation territory per
CONTRIBUTION_STANDARDS.md. Generated entries are `status: draft` skeletons
whose facts (verse text, Strong's tags, lexicon data) are reproducible and
verifiable against the pinned sources.
"""

from search.corpus.backup import (
    CURRENT_BACKUP_VERSION,
    export_backup,
    inspect_backup,
    restore_backup,
    verify_backup,
)
from search.corpus.bible_books import (
    BIBLE_BOOKS,
    CANONICAL_OSIS_ORDER,
    NT_BOOKS,
    OT_BOOKS,
    BookInfo,
    get_book_info,
    parse_passage_ref,
    resolve_book_code,
)
from search.corpus.extract_kjv import (
    DEFAULT_BIBLE_DB,
    DEFAULT_KJV_JSON,
    BibleDB,
    clean_token_text,
    clean_verse_text,
    compile_bible_db,
    extract_tokens,
)

__all__ = [
    "BIBLE_BOOKS",
    "CANONICAL_OSIS_ORDER",
    "CURRENT_BACKUP_VERSION",
    "DEFAULT_BIBLE_DB",
    "DEFAULT_KJV_JSON",
    "NT_BOOKS",
    "OT_BOOKS",
    "BibleDB",
    "BookInfo",
    "clean_token_text",
    "clean_verse_text",
    "compile_bible_db",
    "export_backup",
    "extract_tokens",
    "get_book_info",
    "inspect_backup",
    "parse_passage_ref",
    "resolve_book_code",
    "restore_backup",
    "verify_backup",
]
