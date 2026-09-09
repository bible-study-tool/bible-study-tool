"""Pauline Argument Flow & Discourse Markers Engine (ADR-020, WP-025).

Classifies Koine Greek and Biblical Hebrew logical connectors (premises,
conclusions, divine purposes, adversative pivots, analogies, and conditions)
to illuminate the structural train of thought across the epistles and biblical canon.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from rich.markup import escape


class DiscourseCategory(str, Enum):
    """Primary rhetorical categories of logical discourse markers."""

    PREMISE = "PREMISE"          # Ground, Cause, Basis ("Why", "For", "Because")
    CONCLUSION = "CONCLUSION"    # Inference, Turning Point, Deduction ("Therefore", "Wherefore", "So then")
    PURPOSE = "PURPOSE"          # Divine Design, Sovereign Goal ("In order that", "That", "To the end that")
    CONTRAST = "CONTRAST"        # Adversative Pivot, Divine Reversal ("But God", "However", "Yet")
    CONDITION = "CONDITION"      # Covenant Contingency, Supposition ("If... then", "Whether")
    ANALOGY = "ANALOGY"          # Archetype, Divine Pattern ("Just as", "Even as", "According as")


DISCOURSE_CATEGORY_COLORS: dict[DiscourseCategory, str] = {
    DiscourseCategory.PREMISE: "green",
    DiscourseCategory.CONCLUSION: "yellow",
    DiscourseCategory.PURPOSE: "cyan",
    DiscourseCategory.CONTRAST: "red",
    DiscourseCategory.ANALOGY: "magenta",
    DiscourseCategory.CONDITION: "blue",
}


@dataclass(frozen=True)
class DiscourseMarker:
    """Deterministic representation of a logical discourse connector in Scripture."""

    category: DiscourseCategory
    strongs: str               # e.g. "G1063", "G3767", "G2443", "H3588"
    original_word: str         # e.g. "γάρ", "οὖν", "ἵνα", "כִּי"
    transliteration: str       # e.g. "gar", "oun", "hina", "ki"
    english_text: str          # e.g. "For", "therefore", "that", "Because"
    role_label: str            # e.g. "Premise / Explanatory Ground"
    function_summary: str      # High-yield summary of rhetorical purpose
    theological_significance: str  # Deep explanation of how biblical writers employ this particle
    token_index: int = 0
    is_major_pivot: bool = False  # e.g. Romans 12:1 'therefore' or Eph 2:4 'But God'


# ---------------------------------------------------------------------------
# Canonical Lexical Tables for Greek NT Discourse Particles
# ---------------------------------------------------------------------------

_GREEK_DISCOURSE_MAP: dict[str, dict[str, Any]] = {
    "G1063": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "γάρ",
        "transliteration": "gar",
        "typical_english": "for",
        "role_label": "Premise / Explanatory Ground",
        "function_summary": "Explains why: introduces the theological bedrock or reason supporting the preceding assertion.",
        "theological_significance": (
            "Paul's primary logical building block. Frequently stacked in sequence (e.g., Romans 1:16, 17, 18) "
            "to drill down into the deeper spiritual realities and divine causes behind gospel truth."
        ),
    },
    "G3754": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "ὅτι",
        "transliteration": "hoti",
        "typical_english": "because / that",
        "role_label": "Causal Ground / Evidence",
        "function_summary": "States the factual cause or objective evidence: 'because', 'for that', 'seeing that'.",
        "theological_significance": (
            "Points to concrete historical or divine realities as the unshakeable foundation for faith and obedience."
        ),
    },
    "G1360": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "διότι",
        "transliteration": "dioti",
        "typical_english": "forasmuch as / because",
        "role_label": "Direct Ground / Indisputable Cause",
        "function_summary": "Emphatic causal ground: 'on the very account that', 'forasmuch as'.",
        "theological_significance": (
            "Combines 'dia' (through/on account of) and 'hoti' (that) to present an indisputable, binding divine cause."
        ),
    },
    "G1893": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "ἐπεί",
        "transliteration": "epei",
        "typical_english": "since / seeing that",
        "role_label": "Logical Premise / Given Truth",
        "function_summary": "Introduces a foundational given truth: 'since', 'seeing that', 'otherwise'.",
        "theological_significance": (
            "Used in theological argumentation to demonstrate what follows by necessity from an established covenant fact."
        ),
    },
    "G1894": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "ἐπειδή",
        "transliteration": "epeide",
        "typical_english": "inasmuch as",
        "role_label": "Historical / Covenant Premise",
        "function_summary": "States a decisive historical or spiritual reality: 'since indeed', 'inasmuch as'.",
        "theological_significance": (
            "Establishes a covenant premise based on God's decisive past redemptive actions (e.g. 1 Cor 1:21, 22)."
        ),
    },
    "G2530": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "καθότι",
        "transliteration": "kathoti",
        "typical_english": "according as",
        "role_label": "Proportional Ground",
        "function_summary": "According to the reason that: 'inasmuch as', 'because that'.",
        "theological_significance": (
            "Grounds divine justice and human responsibility in proportional spiritual revelation."
        ),
    },
    "G3767": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "οὖν",
        "transliteration": "oun",
        "typical_english": "therefore",
        "role_label": "Deductive Turning Point / Therefore",
        "function_summary": "The supreme transition marker: establishes what follows or pivots from doctrine to holy living.",
        "theological_significance": (
            "Marks the great turning points in Pauline theology (e.g. Romans 12:1, Ephesians 4:1). "
            "Having laid the doctrinal foundation of grace in the preceding chapters, Paul uses 'oun' to declare: "
            "'Because of all God has accomplished for you, THIS is how you must now live.'"
        ),
        "is_major_pivot": True,
    },
    "G686": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "ἄρα",
        "transliteration": "ara",
        "typical_english": "so then",
        "role_label": "Inescapable Inference / So Then",
        "function_summary": "Draws an inescapable deductive conclusion: 'so then', 'consequently', 'therefore'.",
        "theological_significance": (
            "Clinches theological debates by stating the inevitable spiritual reality resulting from the argument "
            "(e.g. Romans 8:1 'There is therefore [ara] now no condemnation...')."
        ),
    },
    "G1352": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "διό",
        "transliteration": "dio",
        "typical_english": "wherefore",
        "role_label": "Direct Inferential Result / Wherefore",
        "function_summary": "Direct inference: 'wherefore', 'on which account', 'for this very reason'.",
        "theological_significance": (
            "Connects ethical imperatives directly to redemptive realities (e.g. Ephesians 4:25 'Wherefore putting away lying...')."
        ),
    },
    "G1355": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "διόπερ",
        "transliteration": "dioper",
        "typical_english": "wherefore especially",
        "role_label": "Urgent Solemn Inference",
        "function_summary": "Emphatic inference pressing immediate personal consecration: 'for which cause especially'.",
        "theological_significance": (
            "Urges immediate radical separation from sin in light of eternal stakes (e.g. 1 Cor 10:14)."
        ),
    },
    "G5620": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "ὥστε",
        "transliteration": "hoste",
        "typical_english": "so that / wherefore",
        "role_label": "Resulting Conclusion / So That",
        "function_summary": "Declares both the resulting consequence and practical takeaway: 'so then', 'with the result that'.",
        "theological_significance": (
            "Bridges the gap between theological reality and practical fruit in the believer's character."
        ),
    },
    "G5106": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "τοιγαροῦν",
        "transliteration": "toigaroun",
        "typical_english": "consequently therefore",
        "role_label": "Solemn Covenant Conclusion",
        "function_summary": "Formal, majestic conclusion: 'wherefore then', 'consequently therefore'.",
        "theological_significance": (
            "Introduces high-stakes covenant exhortations (e.g. Hebrews 12:1 'Wherefore seeing we also are compassed about...')."
        ),
        "is_major_pivot": True,
    },
    "G5105": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "τοίνυν",
        "transliteration": "toinun",
        "typical_english": "therefore now",
        "role_label": "Immediate Practical Deduction",
        "function_summary": "Direct practical inference: 'therefore now', 'accordingly'.",
        "theological_significance": (
            "Commands immediate action in light of truth already settled (e.g. 1 Cor 9:26, Heb 13:13)."
        ),
    },
    "G2443": {
        "category": DiscourseCategory.PURPOSE,
        "original_word": "ἵνα",
        "transliteration": "hina",
        "typical_english": "in order that / that",
        "role_label": "Divine Purpose / Sovereign Design",
        "function_summary": "Identifies divine purpose or covenant aim: 'in order that', 'to the end that', 'so that'.",
        "theological_significance": (
            "Expresses God's intentional teleology in election, redemption, and sanctification. "
            "Answers the question: 'Unto what eternal end did God do this?' (e.g. Eph 1:4 'that we should be holy', Gal 4:5)."
        ),
        "is_major_pivot": True,
    },
    "G3704": {
        "category": DiscourseCategory.PURPOSE,
        "original_word": "ὅπως",
        "transliteration": "hopos",
        "typical_english": "so that / in order that",
        "role_label": "Deliberate Purpose / Goal",
        "function_summary": "Declares the deliberate purpose or method: 'in order that', 'that thereby'.",
        "theological_significance": (
            "Emphasizes the purposeful alignment of divine means with sovereign redemptive ends."
        ),
    },
    "G235": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "ἀλλά",
        "transliteration": "alla",
        "typical_english": "but / on the contrary",
        "role_label": "Strong Adversative / Holy Contrast",
        "function_summary": "Sharp, decisive contrast: 'but', 'on the contrary', 'yet'.",
        "theological_significance": (
            "Shatters human pretension or legalism to magnify divine grace and sovereign righteousness. "
            "Replaces human failure with God's miraculous provision."
        ),
        "is_major_pivot": True,
    },
    "G1161": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "δέ",
        "transliteration": "de",
        "typical_english": "but / now",
        "role_label": "Transitional Pivot / Contrast",
        "function_summary": "Transitional or contrastive connector: 'but', 'now', 'on the other hand'.",
        "theological_significance": (
            "When coupled with God ('ho de theos'), introduces the glorious 'But God' redemptive reversals "
            "where divine mercy interrupts human ruin and death (e.g. Ephesians 2:4, Romans 5:8)."
        ),
    },
    "G4133": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "πλήν",
        "transliteration": "plen",
        "typical_english": "nevertheless",
        "role_label": "Qualifying Adversative / Nevertheless",
        "function_summary": "Refocuses or sets boundaries: 'nevertheless', 'howbeit', 'notwithstanding'.",
        "theological_significance": (
            "Cuts through secondary debates to re-anchor the soul in what is supreme."
        ),
    },
    "G3305": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "μέντοι",
        "transliteration": "mentoi",
        "typical_english": "yet however",
        "role_label": "Concessive Contrast / Yet Truly",
        "function_summary": "Concedes a point while asserting an overriding truth: 'yet however', 'nevertheless'.",
        "theological_significance": (
            "Acknowledges present earthly realities while maintaining the superiority of spiritual truth."
        ),
    },
    "G1487": {
        "category": DiscourseCategory.CONDITION,
        "original_word": "εἰ",
        "transliteration": "ei",
        "typical_english": "if",
        "role_label": "Condition / Given Supposition",
        "function_summary": "States a condition assumed true for the argument: 'if', 'since it is so'.",
        "theological_significance": (
            "In first-class conditions, Paul assumes the truth of the premise ('If God be for us [and He is!], who can be against us?')."
        ),
    },
    "G1437": {
        "category": DiscourseCategory.CONDITION,
        "original_word": "ἐάν",
        "transliteration": "ean",
        "typical_english": "if on condition",
        "role_label": "Contingent Condition / If Ever",
        "function_summary": "Specifies a conditional contingency or covenant responsibility: 'if ever', 'on condition that'.",
        "theological_significance": (
            "Presents real covenant conditions regarding faith, abiding, and obedience in the Christian walk."
        ),
    },
    "G1535": {
        "category": DiscourseCategory.CONDITION,
        "original_word": "εἴτε",
        "transliteration": "eite",
        "typical_english": "whether",
        "role_label": "Comprehensive Supposition",
        "function_summary": "Covers all contingencies: 'whether... or'.",
        "theological_significance": (
            "Demonstrates that in every possible circumstance of life or death, Christ remains Lord (e.g. Rom 14:8)."
        ),
    },
    "G2531": {
        "category": DiscourseCategory.ANALOGY,
        "original_word": "καθώς",
        "transliteration": "kathos",
        "typical_english": "just as / according as",
        "role_label": "Divine Pattern / Just As",
        "function_summary": "Connects action to divine archetype: 'just as', 'even as', 'according as'.",
        "theological_significance": (
            "Anchors Christian ethics directly in the character, election, and self-sacrificing love of Christ "
            "(e.g. Ephesians 5:2 'walk in love, as Christ also hath loved us', Ephesians 5:25)."
        ),
        "is_major_pivot": True,
    },
    "G5618": {
        "category": DiscourseCategory.ANALOGY,
        "original_word": "ὥσπερ",
        "transliteration": "hosper",
        "typical_english": "even as",
        "role_label": "Formal Analogy / Even As",
        "function_summary": "Exact parallel comparison: 'just as', 'even as'.",
        "theological_significance": (
            "Structures profound theological typologies between Adam and Christ (e.g. Romans 5:12, 19)."
        ),
    },
    "G5613": {
        "category": DiscourseCategory.ANALOGY,
        "original_word": "ὡς",
        "transliteration": "hos",
        "typical_english": "as / like as",
        "role_label": "Comparative Model / As",
        "function_summary": "Draws spiritual comparison: 'as', 'like as', 'even as'.",
        "theological_significance": (
            "Calls the believer to mirror heavenly realities in daily conduct."
        ),
    },
    "G3779": {
        "category": DiscourseCategory.ANALOGY,
        "original_word": "οὕτως",
        "transliteration": "houtos",
        "typical_english": "so / thus also",
        "role_label": "Correlative Fulfillment / So Also",
        "function_summary": "Marks the correlative completion of an analogy: 'so', 'in this manner', 'thus also'.",
        "theological_significance": (
            "Completes the 'Just as... SO ALSO' theological movement, applying Christ's triumph directly to believers."
        ),
    },
}


# ---------------------------------------------------------------------------
# Canonical Lexical Tables for Hebrew OT Discourse Particles (Normalized Keys)
# ---------------------------------------------------------------------------

_HEBREW_DISCOURSE_MAP: dict[str, dict[str, Any]] = {
    "H3588": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "כִּי",
        "transliteration": "ki",
        "typical_english": "for / because",
        "role_label": "Foundational Premise / For, Because",
        "function_summary": "Explains why: the central explanatory and causal particle throughout the Hebrew Bible.",
        "theological_significance": (
            "Introduces the divine rationale, motivation, or covenant reason behind God's commands, judgments, and promises."
        ),
    },
    "H3282": {
        "category": DiscourseCategory.PREMISE,
        "original_word": "יַעַן",
        "transliteration": "ya'an",
        "typical_english": "because that",
        "role_label": "Covenant Cause / Because That",
        "function_summary": "States the moral cause or judicial reason: 'because that', 'on account of'.",
        "theological_significance": (
            "Frequently introduces prophetic verdicts, linking consequences directly to obedience or transgression."
        ),
    },
    "H3651": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "עַל־כֵּן / כֵּן",
        "transliteration": "al-ken / ken",
        "typical_english": "therefore / so",
        "role_label": "Covenant Inference / Therefore",
        "function_summary": "Establishes an enduring principle or ethical conclusion: 'therefore', 'for this cause'.",
        "theological_significance": (
            "Marks seminal covenant conclusions (e.g. Genesis 2:24 'Therefore shall a man leave his father and mother...')."
        ),
        "is_major_pivot": True,
    },
    "H3926": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "לָכֵן",
        "transliteration": "lakhen",
        "typical_english": "therefore assuredly",
        "role_label": "Prophetic Turning Point / Therefore",
        "function_summary": "The authoritative prophetic transition: 'therefore assuredly'.",
        "theological_significance": (
            "Precedes divine announcements where the Lord announces His sovereign intervention in history."
        ),
        "is_major_pivot": True,
    },
    "H6258": {
        "category": DiscourseCategory.CONCLUSION,
        "original_word": "עַתָּה",
        "transliteration": "attah",
        "typical_english": "and now therefore",
        "role_label": "Urgent Present Application / And Now",
        "function_summary": "Moves from historical reflection to immediate decision: 'and now therefore'.",
        "theological_significance": (
            "Demands a present choice in response to what God has revealed or done."
        ),
    },
    "H4616": {
        "category": DiscourseCategory.PURPOSE,
        "original_word": "לְמַעַן",
        "transliteration": "lema'an",
        "typical_english": "in order that",
        "role_label": "Divine Purpose / In Order That",
        "function_summary": "Declares God's ultimate purpose or glory: 'in order that', 'for the sake of', 'to the intent that'.",
        "theological_significance": (
            "Expresses the supreme goal of redemption: 'that they may know that I am the LORD' or 'for My name's sake'."
        ),
        "is_major_pivot": True,
    },
    "H6435": {
        "category": DiscourseCategory.PURPOSE,
        "original_word": "פֶּן",
        "transliteration": "pen",
        "typical_english": "lest",
        "role_label": "Preventative Purpose / Lest",
        "function_summary": "Expresses holy caution and warning: 'lest', 'so that not'.",
        "theological_significance": (
            "Guards covenant boundaries against spiritual neglect, apostasy, or idolatry."
        ),
    },
    "H199": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "אוּלָם",
        "transliteration": "ulam",
        "typical_english": "but truly",
        "role_label": "Strong Adversative / But Truly",
        "function_summary": "Decisive pivot: 'but indeed', 'howbeit', 'nevertheless'.",
        "theological_significance": (
            "Contrasts human expectation with sovereign divine reality."
        ),
    },
    "H61": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "אֲבָל",
        "transliteration": "aval",
        "typical_english": "truly, but",
        "role_label": "Solemn Contrast / Truly, But",
        "function_summary": "Shatters illusions: 'verily, but', 'yet truly'.",
        "theological_significance": (
            "Highlights uncompromising spiritual truth against deception."
        ),
    },
    "H389": {
        "category": DiscourseCategory.CONTRAST,
        "original_word": "אַךְ",
        "transliteration": "akh",
        "typical_english": "surely / yet",
        "role_label": "Restrictive Adversative / Surely, Yet",
        "function_summary": "Focuses on the sole essential truth: 'surely', 'only', 'yet nevertheless'.",
        "theological_significance": (
            "Affirms steadfast trust in God alone amid trials (e.g. Psalm 62:1 'Truly [akh] my soul waiteth upon God')."
        ),
    },
    "H518": {
        "category": DiscourseCategory.CONDITION,
        "original_word": "אִם",
        "transliteration": "im",
        "typical_english": "if",
        "role_label": "Covenant Condition / If",
        "function_summary": "States covenant contingencies: 'if', 'whether'.",
        "theological_significance": (
            "Central to the covenant promises and blessings of Deuteronomy and Leviticus."
        ),
    },
    "H3863": {
        "category": DiscourseCategory.CONDITION,
        "original_word": "לוּ",
        "transliteration": "lu",
        "typical_english": "if only",
        "role_label": "Heartfelt Longing / If Only",
        "function_summary": "Expresses earnest divine or human desire: 'if only', 'would that'.",
        "theological_significance": (
            "Reveals God's compassionate yearning for His people's repentance (e.g. Isaiah 48:18)."
        ),
    },
}


def _canonical_strongs(code: str) -> str:
    """Normalize Strong's code to letter + unpadded integer string (e.g. H0199 -> H199)."""
    c = code.upper().strip()
    if len(c) > 1 and c[0] in ("H", "G") and c[1:].isdigit():
        return f"{c[0]}{int(c[1:])}"
    return c


# ---------------------------------------------------------------------------
# Extraction Engine
# ---------------------------------------------------------------------------

def extract_verse_discourse_markers(
    tokens: list[dict[str, Any]],
    text: str = "",
    verse_osis: str = "",
) -> list[DiscourseMarker]:
    """Extract and classify all discourse connectors present in a verse's token stream."""
    markers: list[DiscourseMarker] = []
    seen_categories_and_words: set[tuple[str, str]] = set()

    for tok_idx, tok in enumerate(tokens):
        s_list = tok.get("strongs", [])
        if isinstance(s_list, str):
            s_list = [s_list]
        eng_text = tok.get("text", "").strip()

        for s_code in s_list:
            canon_code = _canonical_strongs(s_code)
            # 1. Check Greek
            if canon_code in _GREEK_DISCOURSE_MAP:
                meta = _GREEK_DISCOURSE_MAP[canon_code]
                cat = meta["category"]
                orig_word = meta["original_word"]
                key = (cat.value, orig_word)
                if key not in seen_categories_and_words:
                    seen_categories_and_words.add(key)
                    disp_eng = eng_text or meta.get("typical_english", "")
                    markers.append(
                        DiscourseMarker(
                            category=cat,
                            strongs=canon_code,
                            original_word=orig_word,
                            transliteration=meta["transliteration"],
                            english_text=disp_eng,
                            role_label=meta["role_label"],
                            function_summary=meta["function_summary"],
                            theological_significance=meta["theological_significance"],
                            token_index=tok_idx,
                            is_major_pivot=meta.get("is_major_pivot", False),
                        )
                    )

            # 2. Check Hebrew
            elif canon_code in _HEBREW_DISCOURSE_MAP:
                meta = _HEBREW_DISCOURSE_MAP[canon_code]
                cat = meta["category"]
                orig_word = meta["original_word"]
                key = (cat.value, orig_word)
                if key not in seen_categories_and_words:
                    seen_categories_and_words.add(key)
                    disp_eng = eng_text or meta.get("typical_english", "")
                    markers.append(
                        DiscourseMarker(
                            category=cat,
                            strongs=canon_code,
                            original_word=orig_word,
                            transliteration=meta["transliteration"],
                            english_text=disp_eng,
                            role_label=meta["role_label"],
                            function_summary=meta["function_summary"],
                            theological_significance=meta["theological_significance"],
                            token_index=tok_idx,
                            is_major_pivot=meta.get("is_major_pivot", False),
                        )
                    )

    # Secondary check: English phrase detection if no Strong's matched or for compound markers
    if not markers and text:
        text_lower = text.lower().strip()
        if text_lower.startswith("wherefore") or text_lower.startswith("therefore"):
            markers.append(
                DiscourseMarker(
                    category=DiscourseCategory.CONCLUSION,
                    strongs="",
                    original_word="Inference",
                    transliteration="conclusion",
                    english_text=text.split()[0],
                    role_label="Deductive Turning Point / Therefore",
                    function_summary="Establishes what follows from the preceding truth.",
                    theological_significance="Draws the practical and ethical conclusion from foundational doctrine.",
                    token_index=0,
                    is_major_pivot=True,
                )
            )
        elif text_lower.startswith("for ") or text_lower.startswith("because "):
            markers.append(
                DiscourseMarker(
                    category=DiscourseCategory.PREMISE,
                    strongs="",
                    original_word="Premise",
                    transliteration="premise",
                    english_text=text.split()[0],
                    role_label="Premise / Explanatory Ground",
                    function_summary="Explains why: provides the theological reason for the preceding truth.",
                    theological_significance="Introduces the doctrinal foundation supporting the assertion.",
                    token_index=0,
                )
            )

    return markers


def extract_passage_discourse_batch(
    verses_raw: list[dict[str, Any]],
) -> dict[str, list[DiscourseMarker]]:
    """Batch-extract discourse markers for all verses in a passage in a single fast pass."""
    batch_map: dict[str, list[DiscourseMarker]] = {}
    for vr in verses_raw:
        verse_id = f"{vr.get('osis', '')}.{vr.get('chapter', 1)}.{vr.get('verse', 1)}"
        tokens = vr.get("tokens", [])
        text = vr.get("clean_text") or vr.get("text", "")
        markers = extract_verse_discourse_markers(tokens, text=text)
        batch_map[verse_id] = markers
    return batch_map


def format_discourse_badge(markers: list[DiscourseMarker]) -> str:
    """Format a compact, color-coded cue badge for reader pane verse headers."""
    if not markers:
        return ""

    cues: list[str] = []
    for m in markers:
        tag = escape(m.original_word or m.transliteration)
        color = DISCOURSE_CATEGORY_COLORS.get(m.category, "white")
        label_prefix = {
            DiscourseCategory.PREMISE: "Premise",
            DiscourseCategory.CONCLUSION: "Therefore",
            DiscourseCategory.PURPOSE: "Purpose",
            DiscourseCategory.CONTRAST: "Contrast",
            DiscourseCategory.ANALOGY: "Pattern",
            DiscourseCategory.CONDITION: "If",
        }.get(m.category, "Discourse")
        cues.append(f"[bold {color}]⟨{label_prefix}: {tag}⟩[/bold {color}]")

    return " ".join(cues)


# ---------------------------------------------------------------------------
# Argument Flow Analysis for Passages
# ---------------------------------------------------------------------------

@dataclass
class ArgumentFlowStep:
    """A step in the logical progression of an epistle or passage."""

    osis: str
    chapter: int
    verse: int
    text_snippet: str
    markers: list[DiscourseMarker]
    primary_role: str
    flow_description: str


def analyze_passage_argument_flow(
    verses: list[dict[str, Any]],
    markers_by_verse: dict[str, list[DiscourseMarker]] | None = None,
) -> list[ArgumentFlowStep]:
    """Analyze the sequential logical argument flow across an entire passage."""
    steps: list[ArgumentFlowStep] = []
    premise_streak = 0

    for v in verses:
        osis = v.get("osis", "")
        ch = v.get("chapter", 1)
        v_num = v.get("verse", 1)
        verse_id = f"{osis}.{ch}.{v_num}" if osis else f"{ch}:{v_num}"
        raw_text = v.get("clean_text") or v.get("text", "")
        snippet = raw_text[:75] + ("..." if len(raw_text) > 75 else "")

        if markers_by_verse is not None and verse_id in markers_by_verse:
            markers = markers_by_verse[verse_id]
        else:
            tokens = v.get("tokens", [])
            markers = extract_verse_discourse_markers(tokens, text=raw_text)

        # Determine the primary logical movement
        primary_role = "Progression / Elaboration"
        flow_desc = "Continues and unfolds the established train of thought."

        categories = [m.category for m in markers]

        if DiscourseCategory.CONCLUSION in categories:
            premise_streak = 0
            m_concl = next(m for m in markers if m.category == DiscourseCategory.CONCLUSION)
            primary_role = "Conclusion / Turning Point"
            flow_desc = f"Pivots decisively with '{m_concl.english_text}' ({m_concl.original_word}): {m_concl.function_summary}"
        elif DiscourseCategory.PREMISE in categories:
            premise_streak += 1
            m_prem = next(m for m in markers if m.category == DiscourseCategory.PREMISE)
            if premise_streak > 1:
                primary_role = f"Deepening Premise (Ground #{premise_streak})"
                flow_desc = f"Deepens the argument with '{m_prem.english_text}' ({m_prem.original_word}): uncovers the divine bedrock beneath the preceding truth."
            else:
                primary_role = "Premise / Explanatory Ground"
                flow_desc = f"States the foundation with '{m_prem.english_text}' ({m_prem.original_word}): explains why the preceding assertion is true."
        elif DiscourseCategory.PURPOSE in categories:
            premise_streak = 0
            m_purp = next(m for m in markers if m.category == DiscourseCategory.PURPOSE)
            primary_role = "Divine Purpose / Sovereign Design"
            flow_desc = f"Unveils God's intended outcome with '{m_purp.english_text}' ({m_purp.original_word}): specifies the eternal goal or covenant intent."
        elif DiscourseCategory.CONTRAST in categories:
            premise_streak = 0
            m_cont = next(m for m in markers if m.category == DiscourseCategory.CONTRAST)
            primary_role = "Adversative Contrast / Redirection"
            flow_desc = f"Introduces a holy contrast with '{m_cont.english_text}' ({m_cont.original_word}): redirects attention from human limits to divine grace."
        elif DiscourseCategory.ANALOGY in categories:
            premise_streak = 0
            m_ana = next(m for m in markers if m.category == DiscourseCategory.ANALOGY)
            primary_role = "Divine Pattern / Archetype"
            flow_desc = f"Anchors in the divine model with '{m_ana.english_text}' ({m_ana.original_word}): models the command after Christ's character or action."
        elif DiscourseCategory.CONDITION in categories:
            premise_streak = 0
            m_cond = next(m for m in markers if m.category == DiscourseCategory.CONDITION)
            primary_role = "Covenant Condition / Contingency"
            flow_desc = f"Establishes contingency with '{m_cond.english_text}' ({m_cond.original_word}): frames the argument conditionally."
        else:
            premise_streak = 0

        steps.append(
            ArgumentFlowStep(
                osis=verse_id,
                chapter=ch,
                verse=v_num,
                text_snippet=snippet,
                markers=markers,
                primary_role=primary_role,
                flow_description=flow_desc,
            )
        )

    return steps
