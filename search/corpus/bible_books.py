"""Authoritative metadata and book catalog for the 66-book biblical canon (WP-019).

Provides:
  - Complete 66-book catalog (Old Testament: 39 books; New Testament: 27 books).
  - Canonical OSIS codes, names, testaments, chapter counts, and verse counts.
  - Robust book alias resolution (abbreviations, Roman numerals, alternate spellings).
  - Passage reference parsing (e.g. 'John 3:16', '1 Cor 13:4-8', 'Dan 8:14', 'Ps 23').
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class BookInfo:
    """Canonical metadata for a single biblical book."""
    osis: str
    name: str
    testament: str  # 'OT' or 'NT'
    order: int      # 1 to 66
    chapters: int   # Total chapters
    verses: int     # Standard KJV verse count


_CANON_DATA = [
    # Old Testament (39 books, 929 chapters, 23,145 KJV verses)
    ("Gen", "Genesis", "OT", 1, 50, 1533),
    ("Exod", "Exodus", "OT", 2, 40, 1213),
    ("Lev", "Leviticus", "OT", 3, 27, 859),
    ("Num", "Numbers", "OT", 4, 36, 1288),
    ("Deut", "Deuteronomy", "OT", 5, 34, 959),
    ("Josh", "Joshua", "OT", 6, 24, 658),
    ("Judg", "Judges", "OT", 7, 21, 618),
    ("Ruth", "Ruth", "OT", 8, 4, 85),
    ("1Sam", "1 Samuel", "OT", 9, 31, 810),
    ("2Sam", "2 Samuel", "OT", 10, 24, 695),
    ("1Kgs", "1 Kings", "OT", 11, 22, 816),
    ("2Kgs", "2 Kings", "OT", 12, 25, 719),
    ("1Chr", "1 Chronicles", "OT", 13, 29, 942),
    ("2Chr", "2 Chronicles", "OT", 14, 36, 822),
    ("Ezra", "Ezra", "OT", 15, 10, 280),
    ("Neh", "Nehemiah", "OT", 16, 13, 406),
    ("Esth", "Esther", "OT", 17, 10, 167),
    ("Job", "Job", "OT", 18, 42, 1070),
    ("Ps", "Psalms", "OT", 19, 150, 2461),
    ("Prov", "Proverbs", "OT", 20, 31, 915),
    ("Eccl", "Ecclesiastes", "OT", 21, 12, 222),
    ("Song", "Song of Solomon", "OT", 22, 8, 117),
    ("Isa", "Isaiah", "OT", 23, 66, 1292),
    ("Jer", "Jeremiah", "OT", 24, 52, 1364),
    ("Lam", "Lamentations", "OT", 25, 5, 154),
    ("Ezek", "Ezekiel", "OT", 26, 48, 1273),
    ("Dan", "Daniel", "OT", 27, 12, 357),
    ("Hos", "Hosea", "OT", 28, 14, 197),
    ("Joel", "Joel", "OT", 29, 3, 73),
    ("Amos", "Amos", "OT", 30, 9, 146),
    ("Obad", "Obadiah", "OT", 31, 1, 21),
    ("Jonah", "Jonah", "OT", 32, 4, 48),
    ("Mic", "Micah", "OT", 33, 7, 105),
    ("Nah", "Nahum", "OT", 34, 3, 47),
    ("Hab", "Habakkuk", "OT", 35, 3, 56),
    ("Zeph", "Zephaniah", "OT", 36, 3, 53),
    ("Hag", "Haggai", "OT", 37, 2, 38),
    ("Zech", "Zechariah", "OT", 38, 14, 211),
    ("Mal", "Malachi", "OT", 39, 4, 55),

    # New Testament (27 books, 260 chapters, 7,957 KJV verses)
    ("Matt", "Matthew", "NT", 40, 28, 1071),
    ("Mark", "Mark", "NT", 41, 16, 678),
    ("Luke", "Luke", "NT", 42, 24, 1151),
    ("John", "John", "NT", 43, 21, 879),
    ("Acts", "Acts", "NT", 44, 28, 1007),
    ("Rom", "Romans", "NT", 45, 16, 433),
    ("1Cor", "1 Corinthians", "NT", 46, 16, 437),
    ("2Cor", "2 Corinthians", "NT", 47, 13, 257),
    ("Gal", "Galatians", "NT", 48, 6, 149),
    ("Eph", "Ephesians", "NT", 49, 6, 155),
    ("Phil", "Philippians", "NT", 50, 4, 104),
    ("Col", "Colossians", "NT", 51, 4, 95),
    ("1Thess", "1 Thessalonians", "NT", 52, 5, 89),
    ("2Thess", "2 Thessalonians", "NT", 53, 3, 47),
    ("1Tim", "1 Timothy", "NT", 54, 6, 113),
    ("2Tim", "2 Timothy", "NT", 55, 4, 83),
    ("Titus", "Titus", "NT", 56, 3, 46),
    ("Phlm", "Philemon", "NT", 57, 1, 25),
    ("Heb", "Hebrews", "NT", 58, 13, 303),
    ("Jas", "James", "NT", 59, 5, 108),
    ("1Pet", "1 Peter", "NT", 60, 5, 105),
    ("2Pet", "2 Peter", "NT", 61, 3, 61),
    ("1John", "1 John", "NT", 62, 5, 105),
    ("2John", "2 John", "NT", 63, 1, 13),
    ("3John", "3 John", "NT", 64, 1, 14),
    ("Jude", "Jude", "NT", 65, 1, 25),
    ("Rev", "Revelation", "NT", 66, 22, 404),
]

BIBLE_BOOKS: dict[str, BookInfo] = {
    item[0]: BookInfo(
        osis=item[0],
        name=item[1],
        testament=item[2],
        order=item[3],
        chapters=item[4],
        verses=item[5],
    )
    for item in _CANON_DATA
}

CANONICAL_OSIS_ORDER: list[str] = [item[0] for item in _CANON_DATA]
OT_BOOKS: list[str] = [item[0] for item in _CANON_DATA if item[2] == "OT"]
NT_BOOKS: list[str] = [item[0] for item in _CANON_DATA if item[2] == "NT"]

# Multi-variant alias dictionary covering abbreviations, Roman numerals, and scrolls
BOOK_ALIASES: dict[str, str] = {
    # Old Testament
    "GENESIS": "Gen", "GEN": "Gen", "GE": "Gen", "GN": "Gen",
    "EXODUS": "Exod", "EXO": "Exod", "EXOD": "Exod", "EX": "Exod",
    "LEVITICUS": "Lev", "LEV": "Lev", "LV": "Lev",
    "NUMBERS": "Num", "NUM": "Num", "NM": "Num", "NB": "Num",
    "DEUTERONOMY": "Deut", "DEUT": "Deut", "DEU": "Deut", "DT": "Deut",
    "JOSHUA": "Josh", "JOSH": "Josh", "JOS": "Josh",
    "JUDGES": "Judg", "JUDG": "Judg", "JDG": "Judg", "JG": "Judg", "JUD": "Judg",
    "RUTH": "Ruth", "RUT": "Ruth", "RU": "Ruth",
    "1 SAMUEL": "1Sam", "1SAMUEL": "1Sam", "1SAM": "1Sam", "1SA": "1Sam", "1S": "1Sam",
    "I SAMUEL": "1Sam", "ISAMUEL": "1Sam", "ISAM": "1Sam", "ISA": "1Sam",
    "FIRST SAMUEL": "1Sam", "1ST SAMUEL": "1Sam",
    "2 SAMUEL": "2Sam", "2SAMUEL": "2Sam", "2SAM": "2Sam", "2SA": "2Sam", "2S": "2Sam",
    "II SAMUEL": "2Sam", "IISAMUEL": "2Sam", "IISAM": "2Sam", "IISA": "2Sam",
    "SECOND SAMUEL": "2Sam", "2ND SAMUEL": "2Sam",
    "1 KINGS": "1Kgs", "1KINGS": "1Kgs", "1KGS": "1Kgs", "1KI": "1Kgs", "1K": "1Kgs",
    "I KINGS": "1Kgs", "IKINGS": "1Kgs", "IKGS": "1Kgs", "IKI": "1Kgs",
    "FIRST KINGS": "1Kgs", "1ST KINGS": "1Kgs",
    "2 KINGS": "2Kgs", "2KINGS": "2Kgs", "2KGS": "2Kgs", "2KI": "2Kgs", "2K": "2Kgs",
    "II KINGS": "2Kgs", "IIKINGS": "2Kgs", "IIKGS": "2Kgs", "IIKI": "2Kgs",
    "SECOND KINGS": "2Kgs", "2ND KINGS": "2Kgs",
    "1 CHRONICLES": "1Chr", "1CHRONICLES": "1Chr", "1 CHRON": "1Chr", "1CHRON": "1Chr", "1CHR": "1Chr", "1CH": "1Chr",
    "I CHRONICLES": "1Chr", "ICHRONICLES": "1Chr", "I CHRON": "1Chr", "ICHRON": "1Chr", "ICHR": "1Chr", "ICH": "1Chr",
    "FIRST CHRONICLES": "1Chr", "1ST CHRONICLES": "1Chr", "1ST CHRON": "1Chr",
    "2 CHRONICLES": "2Chr", "2CHRONICLES": "2Chr", "2 CHRON": "2Chr", "2CHRON": "2Chr", "2CHR": "2Chr", "2CH": "2Chr",
    "II CHRONICLES": "2Chr", "IICHRONICLES": "2Chr", "II CHRON": "2Chr", "IICHRON": "2Chr", "IICHR": "2Chr", "IICH": "2Chr",
    "SECOND CHRONICLES": "2Chr", "2ND CHRONICLES": "2Chr", "2ND CHRON": "2Chr",
    "EZRA": "Ezra", "EZR": "Ezra",
    "NEHEMIAH": "Neh", "NEH": "Neh", "NE": "Neh",
    "ESTHER": "Esth", "ESTH": "Esth", "EST": "Esth", "ES": "Esth",
    "JOB": "Job", "JB": "Job",
    "PSALMS": "Ps", "PSALM": "Ps", "PSA": "Ps", "PSM": "Ps", "PSS": "Ps", "PS": "Ps",
    "PROVERBS": "Prov", "PROV": "Prov", "PRO": "Prov", "PRV": "Prov", "PR": "Prov",
    "ECCLESIASTES": "Eccl", "ECCL": "Eccl", "ECC": "Eccl", "EC": "Eccl", "QOH": "Eccl", "QOHELETH": "Eccl",
    "SONG OF SOLOMON": "Song", "SONG OF SONGS": "Song", "SONG": "Song", "SOS": "Song", "CANTICLES": "Song", "CANT": "Song",
    "ISAIAH": "Isa", "ISA": "Isa", "IS": "Isa",
    "JEREMIAH": "Jer", "JER": "Jer", "JE": "Jer",
    "LAMENTATIONS": "Lam", "LAM": "Lam", "LA": "Lam",
    "EZEKIEL": "Ezek", "EZEK": "Ezek", "EZE": "Ezek", "EZK": "Ezek",
    "DANIEL": "Dan", "DAN": "Dan", "DN": "Dan",
    "HOSEA": "Hos", "HOS": "Hos", "HO": "Hos",
    "JOEL": "Joel", "JOE": "Joel", "JL": "Joel",
    "AMOS": "Amos", "AMO": "Amos", "AM": "Amos",
    "OBADIAH": "Obad", "OBAD": "Obad", "OBA": "Obad", "OB": "Obad",
    "JONAH": "Jonah", "JON": "Jonah", "JH": "Jonah",
    "MICAH": "Mic", "MIC": "Mic", "MC": "Mic",
    "NAHUM": "Nah", "NAH": "Nah", "NA": "Nah",
    "HABAKKUK": "Hab", "HAB": "Hab", "HB": "Hab",
    "ZEPHANIAH": "Zeph", "ZEPH": "Zeph", "ZEP": "Zeph", "ZP": "Zeph",
    "HAGGAI": "Hag", "HAG": "Hag", "HG": "Hag",
    "ZECHARIAH": "Zech", "ZECH": "Zech", "ZEC": "Zech", "ZC": "Zech",
    "MALACHI": "Mal", "MAL": "Mal", "ML": "Mal",

    # New Testament
    "MATTHEW": "Matt", "MATT": "Matt", "MAT": "Matt", "MT": "Matt",
    "MARK": "Mark", "MRK": "Mark", "MAR": "Mark", "MK": "Mark",
    "LUKE": "Luke", "LUK": "Luke", "LK": "Luke",
    "JOHN": "John", "JHN": "John", "JOH": "John", "JN": "John",
    "ACTS": "Acts", "ACT": "Acts", "AC": "Acts", "ACTS OF THE APOSTLES": "Acts",
    "ROMANS": "Rom", "ROM": "Rom", "RO": "Rom", "RM": "Rom",
    "1 CORINTHIANS": "1Cor", "1CORINTHIANS": "1Cor", "1COR": "1Cor", "1CO": "1Cor",
    "I CORINTHIANS": "1Cor", "ICORINTHIANS": "1Cor", "ICOR": "1Cor", "ICO": "1Cor",
    "FIRST CORINTHIANS": "1Cor", "1ST CORINTHIANS": "1Cor",
    "2 CORINTHIANS": "2Cor", "2CORINTHIANS": "2Cor", "2COR": "2Cor", "2CO": "2Cor",
    "II CORINTHIANS": "2Cor", "IICORINTHIANS": "2Cor", "IICOR": "2Cor", "IICO": "2Cor",
    "SECOND CORINTHIANS": "2Cor", "2ND CORINTHIANS": "2Cor",
    "GALATIANS": "Gal", "GAL": "Gal", "GA": "Gal",
    "EPHESIANS": "Eph", "EPH": "Eph", "EP": "Eph",
    "PHILIPPIANS": "Phil", "PHIL": "Phil", "PHP": "Phil", "PH": "Phil",
    "COLOSSIANS": "Col", "COL": "Col", "CL": "Col",
    "1 THESSALONIANS": "1Thess", "1THESSALONIANS": "1Thess", "1THESS": "1Thess", "1TH": "1Thess",
    "I THESSALONIANS": "1Thess", "ITHESSALONIANS": "1Thess", "ITHESS": "1Thess", "ITH": "1Thess",
    "FIRST THESSALONIANS": "1Thess", "1ST THESSALONIANS": "1Thess",
    "2 THESSALONIANS": "2Thess", "2THESSALONIANS": "2Thess", "2THESS": "2Thess", "2TH": "2Thess",
    "II THESSALONIANS": "2Thess", "IITHESSALONIANS": "2Thess", "IITHESS": "2Thess", "IITH": "2Thess",
    "SECOND THESSALONIANS": "2Thess", "2ND THESSALONIANS": "2Thess",
    "1 TIMOTHY": "1Tim", "1TIMOTHY": "1Tim", "1TIM": "1Tim", "1TI": "1Tim",
    "I TIMOTHY": "1Tim", "ITIMOTHY": "1Tim", "ITIM": "1Tim", "ITI": "1Tim",
    "FIRST TIMOTHY": "1Tim", "1ST TIMOTHY": "1Tim",
    "2 TIMOTHY": "2Tim", "2TIMOTHY": "2Tim", "2TIM": "2Tim", "2TI": "2Tim",
    "II TIMOTHY": "2Tim", "IITIMOTHY": "2Tim", "IITIM": "2Tim", "IITI": "2Tim",
    "SECOND TIMOTHY": "2Tim", "2ND TIMOTHY": "2Tim",
    "TITUS": "Titus", "TIT": "Titus", "TI": "Titus",
    "PHILEMON": "Phlm", "PHLM": "Phlm", "PHM": "Phlm", "PM": "Phlm",
    "HEBREWS": "Heb", "HEB": "Heb", "HE": "Heb",
    "JAMES": "Jas", "JAS": "Jas", "JM": "Jas", "JAM": "Jas",
    "1 PETER": "1Pet", "1PETER": "1Pet", "1PET": "1Pet", "1PE": "1Pet", "1PT": "1Pet", "1P": "1Pet",
    "I PETER": "1Pet", "IPETER": "1Pet", "IPET": "1Pet", "IPE": "1Pet", "IPT": "1Pet",
    "FIRST PETER": "1Pet", "1ST PETER": "1Pet",
    "2 PETER": "2Pet", "2PETER": "2Pet", "2PET": "2Pet", "2PE": "2Pet", "2PT": "2Pet", "2P": "2Pet",
    "II PETER": "2Pet", "IIPETER": "2Pet", "IIPET": "2Pet", "IIPE": "2Pet", "IIPT": "2Pet",
    "SECOND PETER": "2Pet", "2ND PETER": "2Pet",
    "1 JOHN": "1John", "1JOHN": "1John", "1JN": "1John", "1JO": "1John", "1J": "1John",
    "I JOHN": "1John", "IJOHN": "1John", "IJN": "1John", "IJO": "1John",
    "FIRST JOHN": "1John", "1ST JOHN": "1John",
    "2 JOHN": "2John", "2JOHN": "2John", "2JN": "2John", "2JO": "2John", "2J": "2John",
    "II JOHN": "2John", "IIJOHN": "2John", "IIJN": "2John", "IIJO": "2John",
    "SECOND JOHN": "2John", "2ND JOHN": "2John",
    "3 JOHN": "3John", "3JOHN": "3John", "3JN": "3John", "3JO": "3John", "3J": "3John",
    "III JOHN": "3John", "IIIJOHN": "3John", "IIIJN": "3John", "IIIJO": "3John",
    "THIRD JOHN": "3John", "3RD JOHN": "3John",
    "JUDE": "Jude", "JUD": "Jude", "JD": "Jude",
    "REVELATION": "Rev", "REVELATIONS": "Rev", "THE REVELATION": "Rev", "REV": "Rev", "RE": "Rev", "REVELATION OF JOHN": "Rev", "APOCALYPSE": "Rev", "APOC": "Rev",
}


def resolve_book_code(query: str) -> str:
    """Resolve any English book name, abbreviation, or Roman numeral prefix to canonical OSIS code.

    Examples:
      'Genesis' -> 'Gen'
      '1 Cor' -> '1Cor'
      'I Samuel' -> '1Sam'
      'Revelation of John' -> 'Rev'
      'Ps' -> 'Ps'
    """
    clean = query.strip().rstrip(".").strip()
    # Normalize Roman numerals with spaces: 'I Cor' -> '1 Cor'
    clean_upper = clean.upper()
    if clean_upper in BOOK_ALIASES:
        return BOOK_ALIASES[clean_upper]

    # Try removing internal spaces or hyphens: '1-cor' -> '1COR'
    condensed = re.sub(r"[\s\-_]+", "", clean_upper)
    if condensed in BOOK_ALIASES:
        return BOOK_ALIASES[condensed]

    # Try matching OSIS directly case-insensitively
    for osis in BIBLE_BOOKS:
        if osis.upper() == clean_upper or osis.upper() == condensed:
            return osis

    raise ValueError(f"Unknown biblical book: '{query}'")


def get_book_info(query: str) -> BookInfo:
    """Return BookInfo metadata for any book name or abbreviation."""
    osis = resolve_book_code(query)
    return BIBLE_BOOKS[osis]


def parse_passage_ref(raw: str) -> tuple[str, int, Optional[int], Optional[int]]:
    """Parse a reference string into (osis_book, chapter, start_verse, end_verse).

    Supports:
      'John 3:16'      -> ('John', 3, 16, 16)
      'John 3:16-18'   -> ('John', 3, 16, 18)
      'John 3'         -> ('John', 3, None, None)
      'Gen.1.1'        -> ('Gen', 1, 1, 1)
      '1 Cor 13:4-8'   -> ('1Cor', 13, 4, 8)
      'Ps.51.0b'       -> ('Ps', 51, 0, 0)
    """
    cleaned = raw.strip()
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"\.md$", "", cleaned)
    cleaned = re.sub(r"-kjv$", "", cleaned)

    # 1. Full reference: Book chapter:start_v[-end_v] with colon or period separator
    # e.g. 'John 3:16', 'John 3:16-18', 'John 3:16 - 18', 'Gen.1.1', 'Ps 51:0b'
    m = re.fullmatch(
        r"([0-9A-Za-z\s]+?)[\s._-]+(\d+)[\s]*[:.][\s]*(\d+[a-zA-Z]?)(?:\s*-\s*(\d+[a-zA-Z]?))?",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        book_str = m.group(1).strip()
        osis = resolve_book_code(book_str)
        ch = int(m.group(2))
        v1_str = m.group(3)
        v2_str = m.group(4)

        # Parse v1
        v1_match = re.match(r"^(\d+)", v1_str)
        v1 = int(v1_match.group(1)) if v1_match else 1

        # Parse v2
        if v2_str:
            v2_match = re.match(r"^(\d+)", v2_str)
            v2 = int(v2_match.group(1)) if v2_match else v1
        else:
            v2 = v1
        if v2 < v1:
            raise ValueError(f"Invalid verse range in '{raw}': end verse {v2} < start verse {v1}")
        return osis, ch, v1, v2

    # 2. Hyphenated range without colon or period: Book num1 - num2
    # e.g. 'Jude 5-10', 'Philemon 4-7', 'Genesis 1-3'
    m_range = re.fullmatch(
        r"([0-9A-Za-z\s]+?)[\s._-]+(\d+)\s*-\s*(\d+)",
        cleaned,
        re.IGNORECASE,
    )
    if m_range:
        book_str = m_range.group(1).strip()
        osis = resolve_book_code(book_str)
        n1 = int(m_range.group(2))
        n2 = int(m_range.group(3))
        if n2 < n1:
            kind = "verse" if BIBLE_BOOKS[osis].chapters == 1 else "chapter"
            raise ValueError(f"Invalid {kind} range in '{raw}': end {kind} {n2} < start {kind} {n1}")
        b_info = BIBLE_BOOKS[osis]
        if b_info.chapters == 1:
            return osis, 1, n1, n2
        # Multi-chapter book: default to starting chapter
        return osis, n1, None, None

    # 3. Whole chapter or single-chapter book verse reference (e.g. 'John 3', 'Psalm 23', 'Jude 24')
    m_ch = re.fullmatch(r"([0-9A-Za-z\s]+?)[\s._-]+(\d+)", cleaned, re.IGNORECASE)
    if m_ch:
        book_str = m_ch.group(1).strip()
        osis = resolve_book_code(book_str)
        num = int(m_ch.group(2))
        b_info = BIBLE_BOOKS[osis]
        if b_info.chapters == 1 and num > 1:
            return osis, 1, num, num
        return osis, num, None, None

    # 4. Bare book name or abbreviation (e.g. 'Genesis', 'Gen', '1 Corinthians', 'Rev') -> default to chapter 1
    try:
        osis = resolve_book_code(cleaned)
        return osis, 1, None, None
    except ValueError:
        pass

    raise ValueError(f"Cannot parse biblical passage reference from '{raw}'")
