"""Unit tests for biblical canon metadata and passage parsing (WP-019)."""

from __future__ import annotations

import unittest

from search.corpus.bible_books import (
    BIBLE_BOOKS,
    CANONICAL_OSIS_ORDER,
    NT_BOOKS,
    OT_BOOKS,
    get_book_info,
    parse_passage_ref,
    resolve_book_code,
)


class TestBibleBooks(unittest.TestCase):
    """Verify canonical 66-book catalog, book aliases, and passage parsing."""

    def test_canon_counts(self):
        self.assertEqual(len(BIBLE_BOOKS), 66)
        self.assertEqual(len(CANONICAL_OSIS_ORDER), 66)
        self.assertEqual(len(OT_BOOKS), 39)
        self.assertEqual(len(NT_BOOKS), 27)

        total_ch = sum(b.chapters for b in BIBLE_BOOKS.values())
        self.assertEqual(total_ch, 1189)

        total_vs = sum(b.verses for b in BIBLE_BOOKS.values())
        self.assertEqual(total_vs, 31102)

    def test_book_order(self):
        self.assertEqual(CANONICAL_OSIS_ORDER[0], "Gen")
        self.assertEqual(CANONICAL_OSIS_ORDER[38], "Mal")
        self.assertEqual(CANONICAL_OSIS_ORDER[39], "Matt")
        self.assertEqual(CANONICAL_OSIS_ORDER[65], "Rev")

        for idx, osis in enumerate(CANONICAL_OSIS_ORDER, 1):
            b = get_book_info(osis)
            self.assertEqual(b.order, idx)

    def test_book_alias_resolution(self):
        test_cases = [
            ("Genesis", "Gen"),
            ("gen", "Gen"),
            ("GE", "Gen"),
            ("Exodus", "Exod"),
            ("Exo", "Exod"),
            ("Leviticus", "Lev"),
            ("1 Samuel", "1Sam"),
            ("I Samuel", "1Sam"),
            ("1st Samuel", "1Sam"),
            ("First Samuel", "1Sam"),
            ("2 Kings", "2Kgs"),
            ("II Kings", "2Kgs"),
            ("Psalms", "Ps"),
            ("Psalm", "Ps"),
            ("Ps", "Ps"),
            ("Song of Solomon", "Song"),
            ("Song of Songs", "Song"),
            ("Canticles", "Song"),
            ("Isaiah", "Isa"),
            ("Daniel", "Dan"),
            ("Matthew", "Matt"),
            ("Mt", "Matt"),
            ("John", "John"),
            ("Jn", "John"),
            ("Acts of the Apostles", "Acts"),
            ("Romans", "Rom"),
            ("1 Corinthians", "1Cor"),
            ("I Corinthians", "1Cor"),
            ("1 Cor", "1Cor"),
            ("1cor", "1Cor"),
            ("First Corinthians", "1Cor"),
            ("Philemon", "Phlm"),
            ("Hebrews", "Heb"),
            ("1 Peter", "1Pet"),
            ("I Pet", "1Pet"),
            ("1 John", "1John"),
            ("I Jn", "1John"),
            ("Revelation", "Rev"),
            ("Revelation of John", "Rev"),
            ("Apocalypse", "Rev"),
        ]
        for query, expected_osis in test_cases:
            self.assertEqual(
                resolve_book_code(query),
                expected_osis,
                f"Failed to resolve '{query}' -> '{expected_osis}'",
            )

    def test_unknown_book_raises(self):
        with self.assertRaises(ValueError):
            resolve_book_code("NonExistentBook")

    def test_parse_passage_ref(self):
        # Single verse
        self.assertEqual(parse_passage_ref("John 3:16"), ("John", 3, 16, 16))
        self.assertEqual(parse_passage_ref("Gen.1.1"), ("Gen", 1, 1, 1))
        self.assertEqual(parse_passage_ref("Dan 8:14"), ("Dan", 8, 14, 14))
        self.assertEqual(parse_passage_ref("1 Cor 13:4"), ("1Cor", 13, 4, 4))
        self.assertEqual(parse_passage_ref("Ps 23:1"), ("Ps", 23, 1, 1))

        # Verse range
        self.assertEqual(parse_passage_ref("John 3:16-18"), ("John", 3, 16, 18))
        self.assertEqual(parse_passage_ref("Rev 14:6-12"), ("Rev", 14, 6, 12))
        self.assertEqual(parse_passage_ref("1Cor 13:4-8"), ("1Cor", 13, 4, 8))

        # Whole chapter
        self.assertEqual(parse_passage_ref("John 3"), ("John", 3, None, None))
        self.assertEqual(parse_passage_ref("Psalm 23"), ("Ps", 23, None, None))
        self.assertEqual(parse_passage_ref("Genesis 1"), ("Gen", 1, None, None))

        # Bare book name defaults to chapter 1
        self.assertEqual(parse_passage_ref("Genesis"), ("Gen", 1, None, None))
        self.assertEqual(parse_passage_ref("gen"), ("Gen", 1, None, None))
        self.assertEqual(parse_passage_ref("John"), ("John", 1, None, None))
        self.assertEqual(parse_passage_ref("1 Corinthians"), ("1Cor", 1, None, None))
        self.assertEqual(parse_passage_ref("Revelation"), ("Rev", 1, None, None))

        # Offset verse suffix
        self.assertEqual(parse_passage_ref("Ps 51:0b"), ("Ps", 51, 0, 0))

        # Single-chapter books cited as 'Book Verse'
        self.assertEqual(parse_passage_ref("Jude 24"), ("Jude", 1, 24, 24))
        self.assertEqual(parse_passage_ref("Phlm 9"), ("Phlm", 1, 9, 9))
        self.assertEqual(parse_passage_ref("Obad 15"), ("Obad", 1, 15, 15))
        self.assertEqual(parse_passage_ref("2 John 4"), ("2John", 1, 4, 4))
        self.assertEqual(parse_passage_ref("3 John 11"), ("3John", 1, 11, 11))

        # Single-chapter books cited as 'Book v1-v2'
        self.assertEqual(parse_passage_ref("Jude 5-10"), ("Jude", 1, 5, 10))
        self.assertEqual(parse_passage_ref("Jude 5 - 10"), ("Jude", 1, 5, 10))
        self.assertEqual(parse_passage_ref("Philemon 4-7"), ("Phlm", 1, 4, 7))
        self.assertEqual(parse_passage_ref("Obadiah 10-14"), ("Obad", 1, 10, 14))

        # Whitespace tolerance in ranges
        self.assertEqual(parse_passage_ref("Gen 1:1 - 5"), ("Gen", 1, 1, 5))
        self.assertEqual(parse_passage_ref("John 3:16 - 18"), ("John", 3, 16, 18))
        self.assertEqual(parse_passage_ref("1 Cor 13:4 - 8"), ("1Cor", 13, 4, 8))

        # Multi-chapter range without verse colon defaults to starting chapter
        self.assertEqual(parse_passage_ref("Genesis 1-3"), ("Gen", 1, None, None))
        self.assertEqual(parse_passage_ref("Gen 1-3"), ("Gen", 1, None, None))
        self.assertEqual(parse_passage_ref("John 1 - 2"), ("John", 1, None, None))

        # Unicode en-dash and em-dash normalization
        self.assertEqual(parse_passage_ref("John 3:16–18"), ("John", 3, 16, 18))
        self.assertEqual(parse_passage_ref("Jude 5—10"), ("Jude", 1, 5, 10))

    def test_invalid_passage_raises(self):
        with self.assertRaises(ValueError):
            parse_passage_ref("InvalidPassageStringWithoutNumbers")

        # Inverted range
        with self.assertRaises(ValueError):
            parse_passage_ref("John 3:16-10")

        with self.assertRaises(ValueError):
            parse_passage_ref("Jude 10-5")

        with self.assertRaises(ValueError):
            parse_passage_ref("Genesis 5-1")


if __name__ == "__main__":
    unittest.main()
