"""Grammar Nuance Engine (ADR-0020, WP-024 Phase 2).

Decomposes Hebrew (OSHB/ETCBC) and Greek (Macula Greek/Robinson) verbal
morphology into plain-English theological and linguistic explanations.

Brings original-language depth to everyday Bible students without academic jargon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class GrammarNuance:
    """Plain-English theological and linguistic explanation of a verb form."""

    language: str  # "hebrew", "greek", or "aramaic"
    morph_code: str  # e.g. "Vqp3ms", "V-AMI-3S"
    stem_or_tense: str  # e.g. "Qal (Simple Active)", "Aorist Middle"
    conjugation_or_mood: str  # e.g. "Perfect (Qatal)", "Indicative"
    aspect_meaning: str  # e.g. "Completed historical fact"
    voice: str  # e.g. "Active", "Middle (Personal Interest)", "Passive"
    person_number: str  # e.g. "3rd Person Masculine Singular"
    plain_summary: str  # e.g. "[Qal Perfect] Completed sovereign act of creation"
    theological_nuance: str  # Rich explanatory paragraph
    lemma: str = ""
    text: str = ""
    gloss: str = ""
    strongs: str = ""



# ---------------------------------------------------------------------------
# Hebrew / Aramaic Verbal Constants (OSHB / ETCBC Standards)
# ---------------------------------------------------------------------------

_HEBREW_STEMS: dict[str, tuple[str, str]] = {
    "q": (
        "Qal (Simple Active)",
        "Basic, unmediated action performed directly by the subject. When God is the subject, it emphasizes His sovereign, direct initiative.",
    ),
    "N": (
        "Niphal (Simple Passive / Reflexive)",
        "The passive or reflexive of Qal. The subject receives the action or acts upon oneself (frequently used for divine self-manifestation: God 'making Himself seen').",
    ),
    "p": (
        "Piel (Intensive / Transformative Active)",
        "Intensifies the action or brings an object into a thoroughly transformed state (factitive). Not nominal, but vigorous, operative realization (e.g. sanctifying, blessing abundantly).",
    ),
    "P": (
        "Pual (Intensive Passive)",
        "Passive counterpart to Piel: the subject receives an intensive, thorough divine transformation.",
    ),
    "h": (
        "Hiphil (Causative Active)",
        "The stem of divine causation and initiative: the subject causes an object to perform an action or enter a state (e.g. causes to reign, causes to hear, declares righteous).",
    ),
    "H": (
        "Hophal (Causative Passive)",
        "Passive of Hiphil: the subject is caused by an outside sovereign agent to enter a state or undergo action.",
    ),
    "t": (
        "Hitpael (Reflexive / Iterative / Reciprocal)",
        "Reflexive or repeated personal action. Expresses personal communion, walking habitually back and forth with God (as Enoch walked with God), self-consecration, or fervent intercession.",
    ),
    "v": (
        "Hishtaphel (Reflexive-Causative / Worship)",
        "Prostration in holy awe: causing oneself to bow down in humble adoration and worship before the living Creator.",
    ),
    "o": (
        "Polel (Intensive for Hollow Roots)",
        "Intensive action for hollow or geminate verbal roots (counterpart to Piel), conveying energetic, focused realization.",
    ),
    "r": (
        "Hitpolel (Reflexive for Hollow Roots)",
        "Reflexive or iterative action for hollow or geminate roots (counterpart to Hitpael), conveying mutual or internal movement.",
    ),
    "Q": (
        "Qal Passive",
        "Direct passive of a simple action (the action is directly received from an external source).",
    ),
    "l": (
        "Pilpel (Reduplicated Intensive)",
        "Reduplicated intensive stem denoting vigorous, emphatic, or repeated physical or spiritual action.",
    ),
    "L": (
        "Polpal (Reduplicated Intensive Passive)",
        "Passive counterpart to Pilpel: undergoing vigorous intensive action.",
    ),
    "f": (
        "Hithpalpel (Reduplicated Reflexive)",
        "Reflexive intensive action with reduplicated root.",
    ),
    # Biblical Aramaic stems (Daniel, Ezra)
    "b": ("Peal (Aramaic Simple Active)", "Basic active action in Biblical Aramaic (equivalent to Hebrew Qal)."),
    "c": ("Peil (Aramaic Simple Passive)", "Passive of Peal in Biblical Aramaic."),
    "d": ("Ithpeel (Aramaic Reflexive / Passive)", "Reflexive or passive stem in Biblical Aramaic."),
    "e": ("Pael (Aramaic Intensive Active)", "Intensive active stem in Biblical Aramaic (equivalent to Hebrew Piel)."),
    "m": ("Haphel (Aramaic Causative Active)", "Causative active stem in Biblical Aramaic (equivalent to Hebrew Hiphil)."),
    "g": ("Aphel (Aramaic Causative Active)", "Causative active stem in Aramaic."),
    "u": ("Hophal (Aramaic Causative Passive)", "Causative passive stem in Biblical Aramaic."),
}

_HEBREW_CONJUGATIONS: dict[str, tuple[str, str]] = {
    "p": (
        "Perfect (Qatal)",
        "Completed Aspect — Action viewed as a finished, established fact or certainty from the speaker's vantage point.",
    ),
    "i": (
        "Imperfect (Yiqtol)",
        "Incomplete Aspect — Action in progress, continuous, repeated, habitual, or expected in the future.",
    ),
    "w": (
        "Wayyiqtol (Sequential Imperfect / Narrative Past)",
        "Consecutive Historical Past — Dynamic narrative progression carrying the redemptive story forward ('and He said', 'and it was so').",
    ),
    "q": (
        "Weqatal (Sequential Perfect)",
        "Consecutive Future / Instructional — Prophetic decree, instruction, or future consequence following a command or premise.",
    ),
    "v": (
        "Imperative",
        "Command / Urgent Petition — Direct authoritative injunction or prayerful cry addressed to a 2nd person.",
    ),
    "r": (
        "Participle Active",
        "Continuous Agent Activity — Expresses ongoing, continuous, uninterrupted action of the subject ('the one creating', 'hovering').",
    ),
    "s": (
        "Participle Passive",
        "Enduring Received State — Settled condition resulting from received divine action ('blessed of Yahweh').",
    ),
    "c": (
        "Infinitive Construct",
        "Verbal Noun / Purposive — Expresses divine intent, timing, or manner ('in creating', 'in order to make').",
    ),
    "a": (
        "Infinitive Absolute",
        "Emphatic / Solemn Certainty — Underscores absolute certainty, intensity, or solemnity ('surely die', 'diligently hearken').",
    ),
    "j": (
        "Jussive",
        "Sovereign Decree / Volitional — Third-person divine decree ('Let there be light!') or solemn blessing.",
    ),
    "h": (
        "Cohortative",
        "Divine Counsel / First-Person Will — First-person resolve or mutual divine counsel ('Let Us make man in Our image').",
    ),
}

_PERSON_MAP: dict[str, str] = {
    "1": "1st Person",
    "2": "2nd Person",
    "3": "3rd Person",
}

_GENDER_MAP: dict[str, str] = {
    "m": "Masculine",
    "f": "Feminine",
    "c": "Common",
}

_NUMBER_MAP: dict[str, str] = {
    "s": "Singular",
    "p": "Plural",
    "d": "Dual",
}


# ---------------------------------------------------------------------------
# Greek Verbal Constants (Macula Greek / Robinson / Tauber Standards)
# ---------------------------------------------------------------------------

_GREEK_TENSES: dict[str, tuple[str, str]] = {
    "P": (
        "Present",
        "Imperfective / Continuous Aspect — Action in progress, continuous, or habitual ('is continually doing / practicing as a way of life').",
    ),
    "I": (
        "Imperfect",
        "Past Continuous Aspect — Action that was ongoing, repeated, or attempted in the past ('was continually doing / kept on doing').",
    ),
    "F": (
        "Future",
        "Anticipated / Promised Action — Action anticipated to occur, or solemn divine promise / prophecy.",
    ),
    "A": (
        "Aorist",
        "Punctiliar / Snapshot Aspect — Views the action as a complete whole, summary event, or historical milestone, without detailing duration ('did / took place once for all').",
    ),
    "2A": (
        "Second Aorist",
        "Punctiliar / Snapshot Aspect — Complete historical whole / decisive milestone ('did / took place once for all').",
    ),
    "R": (
        "Perfect",
        "Completed Action with Abiding Results — Action completed in the past that produces an enduring, permanent present reality ('stands accomplished and remains true').",
    ),
    "2R": (
        "Second Perfect",
        "Completed Action with Abiding Results — Decisive completed event with enduring, permanent validity in the present.",
    ),
    "L": (
        "Pluperfect",
        "Past Completed with Past Results — Action completed prior to a past point in time with resulting state then existing.",
    ),
    "2L": (
        "Second Pluperfect",
        "Past Completed Action with Past Enduring Results.",
    ),
}

_GREEK_VOICES: dict[str, tuple[str, str]] = {
    "A": ("Active Voice", "The subject directly performs the action ('God loved')."),
    "M": (
        "Middle Voice (Personal Interest)",
        "The subject acts upon themselves, for their own benefit, or with deep personal investment, loving devotion, or involvement (e.g. God choosing us 'for Himself').",
    ),
    "P": (
        "Passive Voice (Divine Sovereign Action)",
        "The subject receives the action from an external source (frequently the 'Divine Passive', where God is the unstated sovereign actor).",
    ),
    "D": (
        "Middle-Passive Deponent",
        "Middle-Passive in form with active sense, retaining personal engagement or subject involvement.",
    ),
    "O": ("Passive Deponent", "Passive in grammatical form with active meaning."),
    "N": ("Middle or Passive", "Middle or passive in voice."),
}

_GREEK_MOODS: dict[str, tuple[str, str]] = {
    "I": ("Indicative Mood", "Objective reality, certainty, and established fact ('it is so')."),
    "S": ("Subjunctive Mood", "Purpose, possibility, contingency, or divine intention ('in order that we might...')."),
    "O": ("Optative Mood", "Earnest prayer, solemn desire, or wish ('May it never be!')."),
    "M": ("Imperative Mood", "Direct command, divine injunction, or urgent appeal ('abide in Me', 'love one another')."),
    "N": ("Infinitive Mood", "Verbal noun expressing purpose, result, or explanation ('to believe', 'in order to live')."),
    "P": ("Participle Mood", "Verbal adjective expressing attendant circumstance, means, time, or cause ('having believed', 'while walking')."),
}

_GREEK_CASE_MAP: dict[str, str] = {
    "N": "Nominative",
    "V": "Vocative",
    "G": "Genitive",
    "D": "Dative",
    "A": "Accusative",
}


# ---------------------------------------------------------------------------
# High-Impact Theological Lemma Overrides
# ---------------------------------------------------------------------------

_HEBREW_LEMMA_NUANCES: dict[str, dict[str, str]] = {
    "בָּרָא": {
        "q": "Exclusively Divine Initiative: In the Hebrew Bible, God alone is ever the subject of 'bara' in the Qal stem. It denotes effortless, sovereign creation out of nothing (creatio ex nihilo), bringing forth unprecedented reality by divine fiat.",
        "N": "Miraculous Divine Work: Created or brought forth miraculously by Yahweh's sovereign hand.",
    },
    "קָדַשׁ": {
        "p": "Operative Consecration: Thoroughly set apart and transformed into sacred holiness for divine communion.",
        "h": "Causative Sanctification: Yahweh causing His people or Sabbath to enter a consecrated, holy state.",
        "t": "Fervent Self-Consecration: Solemnly purifying and dedicating oneself before the presence of the Lord.",
    },
    "בָּרַךְ": {
        "p": "Operative Divine Blessing: Pronounces abundant, fertile, transforming divine favor and life upon the creature.",
        "P": "Endowed with Divine Blessing: Continuously enriched and protected by the blessing of God.",
    },
    "הָלַךְ": {
        "t": "Habitual Intimate Communion: Moving back and forth habitually in close, unbroken fellowship with God (as Enoch and Noah walked with God).",
    },
    "צָדַק": {
        "h": "Forensic Justification: Declared righteous and vindicated in the supreme court of heaven by divine decree.",
    },
    "שָׁבַת": {
        "q": "Sacred Sabbath Cessation: Ceasing from creative labor not from weariness, but in holy celebration and completion of a perfect work.",
    },
    "חוה": {
        "v": "Humble Adoration: Prostrating oneself in reverent worship before the majestic presence of God.",
    },
}

_GREEK_LEMMA_NUANCES: dict[str, dict[str, str]] = {
    "ἐκλέγω": {
        "M": "Loving Personal Choice: The Middle Voice emphasizes that God chose believers not impersonally, but intimately 'for Himself'—for His own loving delight and eternal fellowship.",
    },
    "σῴζω": {
        "R": "Settled, Enduring Salvation: The Perfect Tense signifies a completed deliverance in the past that stands as a permanent, enduring present reality: you have been saved and remain secure in grace.",
        "P": "Divine Rescue: The Passive Voice underscores that salvation is received wholly as a divine gift, not self-generated.",
    },
    "δικαιόω": {
        "A": "Decisive Justification: The Aorist Tense marks justification as a decisive, unrepeatable judicial verdict rendered by God in history.",
        "P": "Divine Verdict: Declared righteous by God's sovereign pronouncement through faith in Christ.",
    },
    "ἀγαπάω": {
        "A": "Unconditional Historical Gift: Aorist points to the supreme, definitive historical demonstration of divine love at the Cross ('God so loved the world that He gave His only begotten Son').",
        "P": "Continuous Way of Love: Present tense calls for continuous, unceasing active love as a habit of life.",
    },
    "ποιέω": {
        "P": "Habitual Practice: In 1 John, the Present Tense ('does not sin') indicates continuous, habitual practice as a settled lifestyle, rather than isolated human stumbling.",
    },
    "μένω": {
        "P": "Abiding Fellowship: In John 15, the Imperative/Present calls for continuous, uninterrupted communion in Christ as the branch in the vine.",
    },
}


# ---------------------------------------------------------------------------
# Core Parsing & Nuance Generators
# ---------------------------------------------------------------------------

def explain_hebrew_morph(
    morph: str,
    lemma: str = "",
    text: str = "",
    gloss: str = "",
    strongs: str = "",
) -> Optional[GrammarNuance]:
    """Decompose an OSHB/ETCBC Hebrew verbal morphology code into plain-English nuance."""
    if not morph:
        return None

    # Handle Aramaic marker in morphology
    if morph == "ARAM":
        return GrammarNuance(
            language="aramaic",
            morph_code=morph,
            stem_or_tense="Aramaic Verb",
            conjugation_or_mood="Aramaic",
            aspect_meaning="Action in Biblical Aramaic",
            voice="Active / Passive",
            person_number="",
            plain_summary="[Aramaic Verb]",
            theological_nuance="Verbal action in Biblical Aramaic (Daniel / Ezra).",
            lemma=lemma,
            text=text,
            gloss=gloss,
        )

    raw = morph[1:] if morph.startswith(("HV", "AV")) else morph
    if not raw.startswith("V") or len(raw) < 3:
        return None

    stem_char = raw[1]
    aspect_char = raw[2]
    rest = raw[3:].split("/")[0]

    stem_name, stem_desc = _HEBREW_STEMS.get(
        stem_char, (f"Stem '{stem_char}'", "Hebrew verbal stem.")
    )
    conj_name, conj_desc = _HEBREW_CONJUGATIONS.get(
        aspect_char, (f"Conjugation '{aspect_char}'", "Hebrew verbal aspect.")
    )

    # Decode person/gender/number/state
    pn_parts = []
    i = 0
    while i < len(rest):
        ch = rest[i]
        if ch in _PERSON_MAP:
            pn_parts.append(_PERSON_MAP[ch])
        elif ch in _GENDER_MAP:
            pn_parts.append(_GENDER_MAP[ch])
        elif ch in _NUMBER_MAP:
            pn_parts.append(_NUMBER_MAP[ch])
        elif ch == "a":
            pn_parts.append("Absolute")
        elif ch == "c":
            pn_parts.append("Construct")
        i += 1
    person_number = " ".join(pn_parts)

    voice = "Active"
    if stem_char in ("N", "P", "H", "Q", "c", "u"):
        voice = "Passive / Reflexive"
    elif stem_char in ("t", "v", "r", "d", "f"):
        voice = "Reflexive / Iterative"

    # Theological nuance synthesis
    lemma_nuance = ""
    if lemma and lemma in _HEBREW_LEMMA_NUANCES:
        stem_overrides = _HEBREW_LEMMA_NUANCES[lemma]
        if stem_char in stem_overrides:
            lemma_nuance = stem_overrides[stem_char]

    theo_text = lemma_nuance or f"{stem_desc} {conj_desc}"
    plain_summary = f"[{stem_name}] {conj_name}"
    if gloss:
        plain_summary += f" — \"{gloss.replace('.', ' ')}\""

    return GrammarNuance(
        language="hebrew" if stem_char not in ("b", "c", "d", "e", "m", "g", "u") else "aramaic",
        morph_code=morph,
        stem_or_tense=stem_name,
        conjugation_or_mood=conj_name,
        aspect_meaning=conj_desc,
        voice=voice,
        person_number=person_number,
        plain_summary=plain_summary,
        theological_nuance=theo_text.strip(),
        lemma=lemma,
        text=text,
        gloss=gloss,
        strongs=strongs,
    )


def explain_greek_morph(
    morph: str,
    lemma: str = "",
    text: str = "",
    gloss: str = "",
    strongs: str = "",
) -> Optional[GrammarNuance]:
    """Decompose a Macula Greek / Robinson verbal morphology code into plain-English nuance."""
    if not morph or not morph.startswith("V-"):
        return None

    parts = morph.split("-")
    if len(parts) < 2:
        return None

    tvm = parts[1]
    if tvm.startswith("2"):
        if len(tvm) < 4:
            return None
        t_code, v_code, m_code = tvm[:2], tvm[2], tvm[3]
    else:
        if len(tvm) < 3:
            return None
        t_code, v_code, m_code = tvm[0], tvm[1], tvm[2]

    tense_name, tense_desc = _GREEK_TENSES.get(
        t_code, (f"Tense '{t_code}'", "Greek verbal tense.")
    )
    voice_name, voice_desc = _GREEK_VOICES.get(
        v_code, (f"Voice '{v_code}'", "Greek verbal voice.")
    )
    mood_name, mood_desc = _GREEK_MOODS.get(
        m_code, (f"Mood '{m_code}'", "Greek verbal mood.")
    )

    # Decode agreement / inflection
    agr = parts[2] if len(parts) > 2 else ""
    pn_parts = []
    greek_gender = {"M": "Masculine", "F": "Feminine", "N": "Neuter"}
    if len(agr) == 2 and agr[0] in _PERSON_MAP:
        pn_parts = [_PERSON_MAP[agr[0]], _NUMBER_MAP.get(agr[1].lower(), "")]
    elif len(agr) >= 3 and agr[0] in _GREEK_CASE_MAP:
        pn_parts = [_GREEK_CASE_MAP[agr[0]], _NUMBER_MAP.get(agr[1].lower(), ""), greek_gender.get(agr[2], "")]
    else:
        for ch in agr:
            if ch in _PERSON_MAP:
                pn_parts.append(_PERSON_MAP[ch])
            elif ch in _GREEK_CASE_MAP:
                pn_parts.append(_GREEK_CASE_MAP[ch])
            elif ch.lower() in _NUMBER_MAP:
                pn_parts.append(_NUMBER_MAP[ch.lower()])
            elif ch.lower() in _GENDER_MAP:
                pn_parts.append(_GENDER_MAP[ch.lower()])
    person_number = " ".join([p for p in pn_parts if p])

    stem_or_tense = f"{tense_name} {voice_name}"

    # Theological nuance synthesis
    lemma_nuance = ""
    if lemma and lemma in _GREEK_LEMMA_NUANCES:
        overrides = _GREEK_LEMMA_NUANCES[lemma]
        parts = []
        base_t = t_code.lstrip("2")
        if f"{t_code}{v_code}" in overrides:
            parts.append(overrides[f"{t_code}{v_code}"])
        elif f"{base_t}{v_code}" in overrides:
            parts.append(overrides[f"{base_t}{v_code}"])
        else:
            matched_t = overrides.get(t_code) or overrides.get(base_t)
            if matched_t:
                parts.append(matched_t)
            if v_code in overrides:
                parts.append(overrides[v_code])
        if parts:
            lemma_nuance = " ".join(parts)

    theo_text = lemma_nuance or f"{tense_desc} {voice_desc} Expressed in the {mood_name.lower()} ({mood_desc.lower()})."
    plain_summary = f"[{tense_name} {voice_name}] {mood_name}"
    if gloss:
        plain_summary += f" — \"{gloss}\""

    return GrammarNuance(
        language="greek",
        morph_code=morph,
        stem_or_tense=stem_or_tense,
        conjugation_or_mood=mood_name,
        aspect_meaning=tense_desc,
        voice=voice_name,
        person_number=person_number,
        plain_summary=plain_summary,
        theological_nuance=theo_text.strip(),
        lemma=lemma,
        text=text,
        gloss=gloss,
        strongs=strongs,
    )


def explain_morph(
    morph: str,
    lemma: str = "",
    text: str = "",
    gloss: str = "",
    strongs: str = "",
) -> Optional[GrammarNuance]:
    """Universal morphology explainer: detects Hebrew vs Greek automatically."""
    if not morph:
        return None
    if morph.startswith("V-"):
        return explain_greek_morph(morph, lemma=lemma, text=text, gloss=gloss, strongs=strongs)
    if morph.startswith("V") or morph.startswith(("HV", "AV")) or morph == "ARAM":
        return explain_hebrew_morph(morph, lemma=lemma, text=text, gloss=gloss, strongs=strongs)
    return None


def get_verse_grammar_nuances(
    verse_id: str,
    db: Any = None,
) -> list[GrammarNuance]:
    """Retrieve all verbal grammar nuances for a verse directly from Macula SQLite DB."""
    if db is None:
        return []

    # Attempt to normalize ref to canonical format (e.g. John.3.16)
    target_id = verse_id
    try:
        from search.macula.lookup import normalize_verse_ref
        norm = normalize_verse_ref(verse_id)
        if norm:
            target_id = norm
    except Exception:
        pass

    conn = getattr(db, "conn", db)
    try:
        cur = conn.execute(
            """
            SELECT text, lemma, morph, pos, gloss, strongs
            FROM tokens
            WHERE verse_id = ? AND pos = 'verb'
            ORDER BY token_num ASC;
            """,
            (target_id,),
        )
        nuances = []
        for row in cur.fetchall():
            text_val = row["text"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            lemma_val = row["lemma"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
            morph_val = row["morph"] if isinstance(row, dict) or hasattr(row, "keys") else row[2]
            gloss_val = row["gloss"] if isinstance(row, dict) or hasattr(row, "keys") else row[4]
            strongs_val = row["strongs"] if isinstance(row, dict) or hasattr(row, "keys") else row[5]
            gn = explain_morph(
                morph_val,
                lemma=lemma_val,
                text=text_val,
                gloss=gloss_val,
                strongs=strongs_val or "",
            )
            if gn:
                nuances.append(gn)
        return nuances
    except Exception:
        return []


def get_verse_nuance_by_strongs(
    verse_id: str,
    db: Any = None,
) -> dict[str, list[GrammarNuance]]:
    """Retrieve a dictionary mapping Strong's IDs to verbal nuances for a verse."""
    nuances = get_verse_grammar_nuances(verse_id, db=db)
    result: dict[str, list[GrammarNuance]] = {}
    for n in nuances:
        if not n.strongs:
            continue
        sc = n.strongs.upper()
        canon = sc[0] + sc[1:].lstrip("0") if len(sc) > 1 else sc
        for key in {sc, canon}:
            result.setdefault(key, []).append(n)
    return result


def get_verses_grammar_nuances_batch(
    verse_ids: list[str],
    db: Any = None,
) -> dict[str, list[GrammarNuance]]:
    """Retrieve verbal grammar nuances for multiple verses in a fast batch query."""
    if db is None or not verse_ids:
        return {}

    # Map input ref to normalized target ref
    ref_map: dict[str, list[str]] = {}
    for v in verse_ids:
        norm = v
        try:
            from search.macula.lookup import normalize_verse_ref
            norm = normalize_verse_ref(v) or v
        except Exception:
            pass
        ref_map.setdefault(norm, []).append(v)

    unique_targets = list(ref_map.keys())
    placeholders = ",".join("?" * len(unique_targets))

    conn = getattr(db, "conn", db)
    result: dict[str, list[GrammarNuance]] = {v: [] for v in verse_ids}
    try:
        cur = conn.execute(
            f"""
            SELECT verse_id, text, lemma, morph, pos, gloss, strongs
            FROM tokens
            WHERE verse_id IN ({placeholders}) AND pos = 'verb'
            ORDER BY token_num ASC;
            """,
            unique_targets,
        )
        for row in cur.fetchall():
            vid = row["verse_id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
            text_val = row["text"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
            lemma_val = row["lemma"] if isinstance(row, dict) or hasattr(row, "keys") else row[2]
            morph_val = row["morph"] if isinstance(row, dict) or hasattr(row, "keys") else row[3]
            gloss_val = row["gloss"] if isinstance(row, dict) or hasattr(row, "keys") else row[5]
            strongs_val = row["strongs"] if isinstance(row, dict) or hasattr(row, "keys") else row[6]
            gn = explain_morph(
                morph_val,
                lemma=lemma_val,
                text=text_val,
                gloss=gloss_val,
                strongs=strongs_val or "",
            )
            if gn:
                for orig_ref in ref_map.get(vid, [vid]):
                    result.setdefault(orig_ref, []).append(gn)
                if vid not in result:
                    result[vid] = []
                if gn not in result[vid]:
                    result[vid].append(gn)
        return result
    except Exception:
        return result


