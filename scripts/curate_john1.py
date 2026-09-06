"""curate_john1.py — Script to curate John 1 (all 51 verses) for Pillar A3.

Moves John 1 entries from draft to status: review, adding rich cross-references,
theological correlations, and verified study notes while preserving the
deterministic KJV verse text, Strong's tags, and Greek word studies verbatim.
"""

from __future__ import annotations

import re
from pathlib import Path

# Curation date
CURATION_DATE = "2026-09-06"

JOHN1_DIR = Path("materials/bible/nt/john/01")

# Theological curation data for John 1 (51 verses)
JOHN1_CURATION: dict[int, dict] = {
    1: {
        "tags": ["theme/christ", "theme/creation", "theme/origins"],
        "xrefs": [
            {"type": "xref/theme", "target": "gen-1-1-kjv", "note": "In the beginning God created — original creation narrative mirrored by the Logos prologue"},
            {"type": "xref/parallel", "target": "colossians-1-16-17", "note": "By him were all things created, that are in heaven, and that are in earth"},
            {"type": "xref/parallel", "target": "hebrews-1-1-3", "note": "God hath in these last days spoken unto us by his Son, by whom also he made the worlds"},
            {"type": "xref/theme", "target": "revelation-19-13", "note": "His name is called The Word of God"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: Christ the eternal Word, divine pre-existence, creation and deity",
            "*   OT Background: Genesis 1:1 — In the beginning God created the heaven and the earth",
            "*   OT Parallel: Proverbs 8:22-30 — The eternal wisdom of God set up from everlasting",
            "*   NT Parallels: Colossians 1:15-17; Hebrews 1:1-3; 1 John 1:1-2; Revelation 19:13",
            "*   Spirit of Prophecy: The Desire of Ages, Chapter 1 ('God With Us'), pp. 19-26",
        ],
        "notes": [
            "*   **The Eternal Pre-Existence (*En arche*, G1722 G746):** 'In the beginning was the Word' echoes Genesis 1:1 (*Bereshit*). While Moses describes the beginning of spacetime creation, John gazes back into the unoriginated, eternal existence of the Son. Christ did not begin to be; He already *was* when the beginning began.",
            "*   **The Continuous Imperfect (*en*, G1510):** The repeated verb *en* ('was') is in the imperfect active, denoting continuous, uninterrupted existence in eternity past. This contrasts sharply with *egeneto* ('came into being', 'was made') in v3 (creation) and v14 (the incarnation).",
            "*   **Face-to-Face Fellowship (*pros ton Theon*, G4314 G3588 G2316):** The preposition *pros* with the accusative conveys active, intimate communion and relational equality: the Word was face-to-face with God, distinct in person yet inseparably united in purpose and love.",
            "*   **Full Deity of the Word (*Theos en ho Logos*, G2316 G1510 G3588 G3056):** In Greek grammar (Colwell's Rule), *Theos* is pre-verbal and anarthrous (lacking the article), functioning as a predicate qualitative noun: 'the Word was deity in essence.' It distinguishes the person of the Word from the Father (*ho Theos*) while asserting His identical divine nature.",
        ],
    },
    2: {
        "tags": ["theme/christ", "theme/covenant"],
        "xrefs": [
            {"type": "xref/theme", "target": "proverbs-8-23", "note": "I was set up from everlasting, from the beginning, or ever the earth was"},
            {"type": "xref/parallel", "target": "john-17-5", "note": "Glorify thou me with thine own self with the glory which I had with thee before the world was"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: Co-eternal communion of Father and Son in the eternal covenant",
            "*   OT Background: Proverbs 8:22-31 — Wisdom rejoicing always before Him",
            "*   NT Parallel: John 17:5, 24 — The Father loved the Son before the foundation of the world",
            "*   Spirit of Prophecy: Patriarchs and Prophets, p. 34 — Christ the Word, the only begotten of God, was one with the eternal Father",
        ],
        "notes": [
            "*   **Reiteration of Eternal Unity:** Verse 2 summarizes the foundational truths of verse 1: the same Word was in the beginning with God. The redemptive mission of Christ was not an afterthought but rooted in eternal co-equality.",
            "*   **Adventist Christological Basis:** Ellen White affirms that 'In Christ is life, original, unborrowed, underived' (DA 530). The Son has existed from eternity with the Father as an active participant in divine counsel.",
        ],
    },
    3: {
        "tags": ["theme/creation", "theme/christ"],
        "xrefs": [
            {"type": "xref/theme", "target": "gen-1-1-kjv", "note": "God created the heaven and the earth — the Word is the active agent of creation"},
            {"type": "xref/parallel", "target": "psalms-33-6", "note": "By the word of the LORD were the heavens made; and all the host of them by the breath of his mouth"},
            {"type": "xref/parallel", "target": "colossians-1-16", "note": "For by him were all things created, that are in heaven, and that are in earth"},
            {"type": "xref/parallel", "target": "hebrews-1-2", "note": "By whom also he made the worlds"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: Christ the divine Creator of all things",
            "*   OT Background: Genesis 1:1; Psalm 33:6, 9; Isaiah 44:24",
            "*   NT Parallels: 1 Corinthians 8:6; Colossians 1:16; Hebrews 1:2, 10-12",
            "*   Spirit of Prophecy: Patriarchs and Prophets, p. 34 — His hands had laid the foundations of the earth and encircled the heavens",
        ],
        "notes": [
            "*   **Exhaustive Agency (*Panta di' autou egeneto*, G3956 G1223 G846 G1096):** 'All things were made through Him.' The comprehensive *panta* leaves no exception. The Father created all things through the Son as the active divine executive.",
            "*   **Antithetical Negation:** John pairs the positive statement with an exhaustive negative: 'and without him was not any thing made that was made.' If anything was created, Christ created it. Therefore, Christ Himself cannot be a created being.",
        ],
    },
    4: {
        "tags": ["theme/christ", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalms-36-9", "note": "For with thee is the fountain of life: in thy light shall we see light"},
            {"type": "xref/parallel", "target": "john-5-26", "note": "As the Father hath life in himself; so hath he given to the Son to have life in himself"},
            {"type": "xref/parallel", "target": "john-8-12", "note": "I am the light of the world: he that followeth me shall not walk in darkness"},
            {"type": "xref/theme", "target": "1-john-1-1-2", "note": "That which was from the beginning... the Word of life"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: Inherent divine life (*zoe*) and illumination (*phos*)",
            "*   OT Background: Genesis 1:3; Psalm 27:1; Psalm 36:9; Proverbs 4:18",
            "*   NT Parallels: John 11:25; 14:6; 1 John 5:11-12",
            "*   Spirit of Prophecy: The Desire of Ages, p. 530 — In Him was life, original, unborrowed, underived",
        ],
        "notes": [
            "*   **Self-Existent Life (*Zoe*, G2222):** Unlike created beings whose life is contingent and derived, life in the Logos is inherent and autonomous (*zoe en auto*). He is the biological, moral, and eternal source of all living existence.",
            "*   **Life as the Light of Humanity:** Life and light are organically linked in Johannine theology: divine life manifests as divine truth, exposing moral darkness and guiding mankind back to God.",
        ],
    },
    5: {
        "tags": ["theme/redemption", "theme/faith"],
        "xrefs": [
            {"type": "xref/theme", "target": "gen-1-4-kjv", "note": "God divided the light from the darkness"},
            {"type": "xref/parallel", "target": "john-3-19", "note": "Light is come into the world, and men loved darkness rather than light"},
            {"type": "xref/parallel", "target": "2-corinthians-4-6", "note": "God, who commanded the light to shine out of darkness, hath shined in our hearts"},
            {"type": "xref/theme", "target": "1-john-1-5", "note": "God is light, and in him is no darkness at all"},
        ],
        "correlations": [
            "*   Theme: The cosmic struggle between divine illumination and spiritual darkness",
            "*   OT Background: Genesis 1:4; Isaiah 9:2; 60:1-2",
            "*   NT Parallels: Ephesians 5:8; 1 Thessalonians 5:5; 1 John 2:8",
            "*   Spirit of Prophecy: The Great Controversy, Introduction — The illumination of the Spirit amidst worldly darkness",
        ],
        "notes": [
            "*   **Inconquerable Light (*phainei*, G5316):** The present tense *phainei* ('shineth') denotes continuous, unceasing radiance. Even in a fallen world shrouded in moral darkness, the divine Light shines without diminution.",
            "*   **Darkness Could Not Overcome (*ou katelaben*, G3756 G2638):** The verb *katalambano* carries a rich double meaning: 'did not comprehend/understand' and 'did not overcome/extinguish.' Satan's realm of darkness has neither understood the revelation of God nor been able to extinguish it.",
        ],
    },
    6: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "malachi-3-1", "note": "Behold, I will send my messenger, and he shall prepare the way before me"},
            {"type": "xref/parallel", "target": "matthew-3-1-3", "note": "In those days came John the Baptist, preaching in the wilderness"},
            {"type": "xref/parallel", "target": "luke-1-17", "note": "He shall go before him in the spirit and power of Elias"},
            {"type": "xref/spirit-prophecy", "target": "des-10-1", "note": "The Desire of Ages, Chapter 10 — 'The Voice in the Wilderness'"},
        ],
        "correlations": [
            "*   Theme: The prophetic forerunner sent from God",
            "*   OT Background: Malachi 3:1; 4:5-6; Isaiah 40:3",
            "*   NT Parallels: Mark 1:2-4; Luke 1:76-79",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 97-108",
        ],
        "notes": [
            "*   **A Man Sent from God (*apesteilmenos*, G649):** The shift from the eternal Word (*Logos*) to a historical human (*anthropos*) is dramatic. John was a commissioned messenger (*apostello*), the boundary between the prophetic dispensation and the arrival of the Messiah.",
        ],
    },
    7: {
        "tags": ["theme/prophecy", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-19", "note": "And this is the record of John, when the Jews sent priests and Levites"},
            {"type": "xref/parallel", "target": "john-5-33-35", "note": "Ye sent unto John, and he bare witness unto the truth"},
            {"type": "xref/parallel", "target": "acts-19-4", "note": "John verily baptized with the baptism of repentance, saying that they should believe on him which should come after"},
        ],
        "correlations": [
            "*   Theme: The purpose of prophetic witness: leading all men to believe",
            "*   NT Parallels: John 3:26-30; 20:31",
            "*   Spirit of Prophecy: The Desire of Ages, p. 100 — Pointing men away from self to the Lamb of God",
        ],
        "notes": [
            "*   **The Witness (*martyria*, G3141):** John's entire mission was subordinate to the Light: to testify (*martyreo*) so that through his testimony all might believe (*pisteusoosin*, G4100). Faith in Christ is the ultimate objective of all true prophetic ministry.",
        ],
    },
    8: {
        "tags": ["theme/christ", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-3-28", "note": "Ye yourselves bear me witness, that I said, I am not the Christ"},
            {"type": "xref/parallel", "target": "matthew-11-11", "note": "Among them that are born of women there hath not risen a greater than John the Baptist"},
        ],
        "correlations": [
            "*   Theme: Humility and clear distinction between the messenger and the Messiah",
            "*   NT Parallels: Acts 13:25; John 3:30",
            "*   Spirit of Prophecy: The Desire of Ages, p. 102 — John disclaimed the honor of being the Messiah",
        ],
        "notes": [
            "*   **Not the Light (*ouk en ekeinos to phos*):** The Gospel author firmly guards against sectarian exaltation of the Baptist. John was a burning and shining lamp (John 5:35), but not the uncreated Light of the World.",
        ],
    },
    9: {
        "tags": ["theme/christ", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "isaiah-49-6", "note": "I will also give thee for a light to the Gentiles, that thou mayest be my salvation unto the end of the earth"},
            {"type": "xref/parallel", "target": "john-8-12", "note": "I am the light of the world"},
            {"type": "xref/parallel", "target": "1-john-2-8", "note": "The darkness is past, and the true light now shineth"},
        ],
        "correlations": [
            "*   Theme: Universal illumination of the True Light",
            "*   OT Background: Isaiah 42:6; 60:1-3",
            "*   NT Parallels: Luke 2:32; Titus 2:11",
            "*   Spirit of Prophecy: The Desire of Ages, p. 464 — Christ's light illuminates every human conscience",
        ],
        "notes": [
            "*   **The True Light (*to phos to alethinon*, G228):** *Alethinos* signifies the genuine, original, ultimate reality as opposed to shadow, copy, or precursor. Christ is the archetypal Light from whom every moral and spiritual illumination derives.",
            "*   **Illuminating Every Person:** Through the conscience, the Holy Spirit, and the works of creation, the divine Light shines upon every human being born into the world (Rom 1:19-20; 2:14-15), leaving none without witness.",
        ],
    },
    10: {
        "tags": ["theme/christ", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "1-corinthians-1-21", "note": "The world by wisdom knew not God"},
            {"type": "xref/parallel", "target": "john-17-25", "note": "O righteous Father, the world hath not known thee"},
            {"type": "xref/theme", "target": "gen-1-1-kjv", "note": "The world made by Him did not recognize its Maker"},
        ],
        "correlations": [
            "*   Theme: The tragedy of the world's spiritual blindness to its Creator",
            "*   OT Background: Isaiah 1:3 — The ox knoweth his owner, but Israel doth not know",
            "*   NT Parallels: 1 Corinthians 2:8; 1 John 3:1",
            "*   Spirit of Prophecy: The Desire of Ages, p. 27 — The Creator was in the world, yet unacknowledged",
        ],
        "notes": [
            "*   **Threefold Kosmos Clause:** 'He was in the world (*kosmos*), and the world was made through Him, and the world knew Him not.' The tragic climax of human rebellion: creation failed to recognize the presence of its own Architect.",
        ],
    },
    11: {
        "tags": ["theme/covenant", "theme/remnant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "luke-19-41-44", "note": "He beheld the city, and wept over it... because thou knewest not the time of thy visitation"},
            {"type": "xref/parallel", "target": "matthew-23-37", "note": "How often would I have gathered thy children together... and ye would not!"},
            {"type": "xref/parallel", "target": "romans-9-1-5", "note": "To whom pertaineth the adoption, and the glory, and the covenants"},
            {"type": "xref/spirit-prophecy", "target": "des-3-1", "note": "The Desire of Ages, Chapter 3 — 'The Fullness of the Time'"},
        ],
        "correlations": [
            "*   Theme: The rejection of the Messiah by His covenant people",
            "*   OT Background: Isaiah 53:3; Jeremiah 2:13",
            "*   NT Parallels: Acts 13:46; Romans 11:1-7",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 31-38",
        ],
        "notes": [
            "*   **His Own Domain and People (*ta idia ... hoi idioi*):** Greek shifts gender: *ta idia* (neuter: His own inheritance/homeland) versus *hoi idioi* (masculine: His own people, the covenant nation). Christ arrived at His own temple and estate, yet His chosen family shut the door against Him.",
        ],
    },
    12: {
        "tags": ["theme/redemption", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "romans-8-14-17", "note": "As many as are led by the Spirit of God, they are the sons of God"},
            {"type": "xref/parallel", "target": "galatians-3-26", "note": "For ye are all the children of God by faith in Christ Jesus"},
            {"type": "xref/parallel", "target": "1-john-3-1-2", "note": "Behold, what manner of love the Father hath bestowed upon us, that we should be called the sons of God"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: Divine adoption and the authority to become children of God",
            "*   OT Background: Hosea 1:10; Isaiah 56:5",
            "*   NT Parallels: Galatians 4:5-7; 2 Peter 1:4",
            "*   Spirit of Prophecy: Steps to Christ, Chapter 5 — Consecration and divine adoption",
        ],
        "notes": [
            "*   **The Authority of Adoption (*exousia*, G1849):** *Exousia* denotes legal right, moral authority, and supernatural empowerment. Those who receive Christ (*elabon*) and believe in His name (*pisteuousin*) receive the status of *tekna Theou* ('children of God by new birth').",
            "*   **Believing in His Name (*eis to onoma autou*):** In Hebrew and Hellenistic thought, the 'name' represents the totality of the person, character, and authority. Faith is personal allegiance and trust in the character of the Incarnate Son.",
        ],
    },
    13: {
        "tags": ["theme/redemption", "theme/holy-spirit"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-3-3-6", "note": "Except a man be born again, he cannot see the kingdom of God... born of the Spirit"},
            {"type": "xref/parallel", "target": "james-1-18", "note": "Of his own will begat he us with the word of truth"},
            {"type": "xref/parallel", "target": "1-peter-1-23", "note": "Being born again, not of corruptible seed, but of incorruptible"},
        ],
        "correlations": [
            "*   Theme: Supernatural regeneration versus human pedigree",
            "*   OT Background: Ezekiel 36:26-27 — A new heart also will I give you",
            "*   NT Parallels: Titus 3:5; 1 John 5:1",
            "*   Spirit of Prophecy: The Desire of Ages, p. 172 — The new birth is a supernatural work of the Holy Spirit",
        ],
        "notes": [
            "*   **Threefold Negative of Human Origin:** Spiritual sonship is not of blood (*haimatoon* — natural descent or pedigree), nor of the will of the flesh (*thelematos sarkos* — physical impulse), nor of the will of man (*thelematos andros* — human resolution or adoption), but directly 'of God' (*ek Theou egennethesan*).",
        ],
    },
    14: {
        "tags": ["theme/christ", "theme/sanctuary", "theme/grace"],
        "xrefs": [
            {"type": "xref/theme", "target": "exodus-25-8", "note": "And let them make me a sanctuary; that I may dwell among them — the tabernacle typology"},
            {"type": "xref/theme", "target": "exodus-33-18-19", "note": "I beseech thee, shew me thy glory... I will make all my goodness pass before thee"},
            {"type": "xref/theme", "target": "exodus-34-6", "note": "Abundant in goodness and truth — translated in the LXX as chesed ve-emet, grace and truth"},
            {"type": "xref/parallel", "target": "hebrews-2-14", "note": "Forasmuch then as the children are partakers of flesh and blood, he also himself likewise took part of the same"},
            {"type": "xref/parallel", "target": "1-timothy-3-16", "note": "God was manifest in the flesh, justified in the Spirit, seen of angels"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: The Incarnation, Sanctuary Tabernacling, Divine Glory, Grace and Truth",
            "*   OT Sanctuary Anchor: Exodus 25:8; 40:34-35; Leviticus 26:11-12; 1 Kings 8:10-11",
            "*   OT Covenant Anchor: Exodus 34:6 (*rav chesed ve-emet* ➔ *pleres charitos kai aletheias*)",
            "*   NT Parallels: Colossians 2:9; Philippians 2:6-8; Revelation 21:3",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 19-26 — The tabernacle pitched among men",
        ],
        "notes": [
            "*   **The Word Became Flesh (*ho Logos sarx egeneto*):** The climax of the prologue. The eternal, self-existent Logos did not merely appear in human likeness (opposing Docetism); He *became* real, tangible human flesh (*sarx*), uniting humanity with unfallen deity forever.",
            "*   **The True Tabernacle (*eskenosen en hemin*, G4637):** The verb *skenoo* means literally 'to pitch a tent / tabernacle.' It anchors directly to the Old Testament sanctuary (*mishkan*, Exodus 25:8). Christ's body was the true sanctuary where the divine presence dwelt among men.",
            "*   **Beholding His Glory (*etheasametha ten doxan autou*):** In the wilderness tabernacle, the *Shekinah* glory filled the Holy of Holies. In Jesus, the eyewitnesses beheld that same glory — not in terrifying unapproachable splendor, but cloaked in self-sacrificing love.",
            "*   **Full of Grace and Truth (*pleres charitos kai aletheias*):** The exact Greek equivalent of the covenant name revealed to Moses on Mount Sinai (Exodus 34:6: *rav chesed ve-emet* — 'abundant in lovingkindness and truth'). The incarnate Christ is the personal embodiment of God's covenant character.",
        ],
    },
    15: {
        "tags": ["theme/christ", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-27", "note": "He it is, who coming after me is preferred before me"},
            {"type": "xref/parallel", "target": "john-1-30", "note": "After me cometh a man which is preferred before me: for he was before me"},
            {"type": "xref/parallel", "target": "matthew-3-11", "note": "He that cometh after me is mightier than I"},
        ],
        "correlations": [
            "*   Theme: Prophetic testimony to the absolute priority and pre-existence of Christ",
            "*   NT Parallels: Colossians 1:18; Hebrews 3:3",
            "*   Spirit of Prophecy: The Desire of Ages, p. 100 — The forerunner's witness to the greater One",
        ],
        "notes": [
            "*   **Chronological Sequence vs. Eternal Priority:** Jesus was born six months after John (Luke 1:26, 36) and began His public ministry after John. Yet John cries: 'He was before me' (*protos mou en*), bearing witness to Christ's absolute pre-temporal existence.",
        ],
    },
    16: {
        "tags": ["theme/grace", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "ephesians-1-7-8", "note": "The riches of his grace, wherein he hath abounded toward us"},
            {"type": "xref/parallel", "target": "colossians-1-19", "note": "For it pleased the Father that in him should all fulness dwell"},
            {"type": "xref/parallel", "target": "colossians-2-9-10", "note": "In him dwelleth all the fulness of the Godhead bodily, and ye are complete in him"},
        ],
        "correlations": [
            "*   Theme: The inexhaustible fullness of Christ and continuous supply of grace",
            "*   OT Background: Psalm 23:5 — My cup runneth over",
            "*   NT Parallels: Romans 5:17, 20-21; 2 Corinthians 12:9",
            "*   Spirit of Prophecy: The Desire of Ages, p. 827 — Grace upon grace for every soul that receives Him",
        ],
        "notes": [
            "*   **Grace for Grace (*charin anti charitos*, G5485 G473):** The preposition *anti* means 'in place of / wave upon wave': as one measure of divine grace is received and experienced, another fresh measure flows to take its place. The fullness (*pleroma*) of Christ is an endless reservoir for believer needs.",
        ],
    },
    17: {
        "tags": ["theme/law", "theme/grace", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "romans-3-21-24", "note": "Being justified freely by his grace through the redemption that is in Christ Jesus"},
            {"type": "xref/parallel", "target": "galatians-3-24", "note": "Wherefore the law was our schoolmaster to bring us unto Christ"},
            {"type": "xref/parallel", "target": "hebrews-3-5-6", "note": "Moses verily was faithful in all his house, as a servant... But Christ as a son over his own house"},
            {"type": "xref/spirit-prophecy", "target": "des-3-1", "note": "The Desire of Ages, Chapter 3 — 'The Fullness of the Time'"},
        ],
        "correlations": [
            "*   Theme: The relationship between the Law given through Moses and Grace/Truth in Christ",
            "*   OT Background: Exodus 20:1-17; Deuteronomy 33:4; Exodus 34:6",
            "*   NT Parallels: Romans 6:14; 10:4; 2 Corinthians 3:6-18",
            "*   Spirit of Prophecy: Mount of Blessing, p. 45 — The law reveals sin, Christ reveals the cure",
        ],
        "notes": [
            "*   **Law and Grace Harmonized:** The contrast is not between a bad law and good grace, but between preparatory revelation and consummation. The law revealed the righteous standard and exposed transgression; in Jesus Christ, the grace to forgive and the truth to transform were realized in living fullness.",
        ],
    },
    18: {
        "tags": ["theme/christ", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/theme", "target": "exodus-33-20", "note": "Thou canst not see my face: for there shall no man see me, and live"},
            {"type": "xref/parallel", "target": "john-6-46", "note": "Not that any man hath seen the Father, save he which is of God, he hath seen the Father"},
            {"type": "xref/parallel", "target": "john-14-9", "note": "He that hath seen me hath seen the Father"},
            {"type": "xref/parallel", "target": "1-timothy-6-16", "note": "Dwelling in the light which no man can approach unto; whom no man hath seen, nor can see"},
            {"type": "xref/spirit-prophecy", "target": "des-1-1", "note": "The Desire of Ages, Chapter 1 — 'God With Us'"},
        ],
        "correlations": [
            "*   Theme: The unique exegesis of the Father through the Only Begotten Son",
            "*   OT Background: Exodus 33:18-23; Isaiah 6:1-5",
            "*   NT Parallels: Colossians 1:15; 1 John 4:12",
            "*   Spirit of Prophecy: The Desire of Ages, p. 19 — Christ came to reveal the Father's character",
        ],
        "notes": [
            "*   **The Ultimate Exegesis (*exegesato*, G1834):** The verb *exegeomai* ('hath declared / unfolded / interpreted') gives us the word 'exegesis'. Jesus did not merely speak about God; His life, character, and sacrifice exegeted the Father's heart to humanity.",
            "*   **In the Bosom of the Father (*eis ton kolpon tou Patros*):** Denotes supreme, perpetual intimacy and shared knowledge within the Godhead.",
        ],
    },
    19: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "luke-3-15", "note": "And as the people were in expectation, and all men mused in their hearts of John, whether he were the Christ"},
            {"type": "xref/parallel", "target": "john-5-33", "note": "Ye sent unto John, and he bare witness unto the truth"},
        ],
        "correlations": [
            "*   Theme: Official Sanhedrin investigation into the ministry of John the Baptist",
            "*   OT Background: Deuteronomy 13:1-5; 18:15-22",
            "*   NT Parallels: Matthew 21:23-27; Mark 11:27-33",
            "*   Spirit of Prophecy: The Desire of Ages, p. 132 — The Sanhedrin's embassy to John",
        ],
        "notes": [
            "*   **The Religious Deputation:** Priests and Levites sent from Jerusalem represented the formal ecclesiastical authority of the nation, investigating whether John claimed messianic or prophetic authority.",
        ],
    },
    20: {
        "tags": ["theme/faith", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-3-28", "note": "Ye yourselves bear me witness, that I said, I am not the Christ, but that I am sent before him"},
            {"type": "xref/parallel", "target": "acts-13-25", "note": "And as John fulfilled his course, he said, Whom think ye that I am? I am not he"},
        ],
        "correlations": [
            "*   Theme: John's emphatic denial of messianic identity",
            "*   NT Parallels: Luke 3:15-16; John 1:8",
            "*   Spirit of Prophecy: The Desire of Ages, p. 133 — John confessed and denied not",
        ],
        "notes": [
            "*   **Emphatic Confession (*homologesen kai ouk ernesato*):** John firmly refused all messianic honors. His loyalty to Christ precluded accepting any inflated human adulation.",
        ],
    },
    21: {
        "tags": ["theme/prophecy", "theme/typology"],
        "xrefs": [
            {"type": "xref/parallel", "target": "malachi-4-5", "note": "Behold, I will send you Elijah the prophet before the coming of the great and dreadful day of the LORD"},
            {"type": "xref/parallel", "target": "deuteronomy-18-15-18", "note": "The LORD thy God will raise up unto thee a Prophet from the midst of thee... like unto me"},
            {"type": "xref/parallel", "target": "matthew-11-14", "note": "And if ye will receive it, this is Elias, which was for to come"},
            {"type": "xref/parallel", "target": "luke-1-17", "note": "In the spirit and power of Elias"},
        ],
        "correlations": [
            "*   Theme: Elijah typology and the promised Prophet of Deuteronomy",
            "*   OT Background: Deuteronomy 18:15; 2 Kings 2:11; Malachi 4:5",
            "*   NT Parallels: Matthew 17:10-13; Mark 9:11-13",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 134-135",
        ],
        "notes": [
            "*   **The Identity Questions:** The delegation asked if John was Elijah (whom Jews expected to return bodily) or 'that Prophet' (Moses' successor in Deut 18:15). John answered 'I am not' to their literalistic misconception, though he came in the 'spirit and power of Elijah' (Luke 1:17).",
        ],
    },
    22: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-19", "note": "The inquiry of the Sanhedrin delegation"},
        ],
        "correlations": [
            "*   Theme: Accountability to the sending authorities",
            "*   Spirit of Prophecy: The Desire of Ages, p. 134",
        ],
        "notes": [
            "*   **Demand for an Official Answer:** The delegates required a definite declaration to report back to the Sanhedrin in Jerusalem.",
        ],
    },
    23: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/theme", "target": "isaiah-40-3", "note": "The voice of him that crieth in the wilderness, Prepare ye the way of the LORD"},
            {"type": "xref/parallel", "target": "matthew-3-3", "note": "For this is he that was spoken of by the prophet Esaias"},
            {"type": "xref/parallel", "target": "mark-1-3", "note": "The voice of one crying in the wilderness"},
            {"type": "xref/parallel", "target": "luke-3-4", "note": "As it is written in the book of the words of Esaias the prophet"},
            {"type": "xref/spirit-prophecy", "target": "des-10-1", "note": "The Desire of Ages, Chapter 10 — 'The Voice in the Wilderness'"},
        ],
        "correlations": [
            "*   Theme: The Voice in the Wilderness preparing the way for YHWH",
            "*   OT Background: Isaiah 40:3-5",
            "*   NT Parallels: Matthew 3:3; Mark 1:3; Luke 3:4-6",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 134-135",
        ],
        "notes": [
            "*   **The Voice, Not the Word:** Christ is the eternal Word (*ho Logos*); John is merely the voice (*phone*) crying in the wilderness. The voice exists only to proclaim the Word.",
            "*   **Preparing the Way of the Lord:** In Isaiah 40:3, the way is prepared for YHWH. In applying this to Jesus, John and the Gospel writers identify Jesus as YHWH manifested in the flesh.",
        ],
    },
    24: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-7", "note": "When he saw many of the Pharisees and Sadducees come to his baptism"},
        ],
        "correlations": [
            "*   Theme: The Pharisaic background of the questioning embassy",
            "*   Spirit of Prophecy: The Desire of Ages, p. 134",
        ],
        "notes": [
            "*   **Pharisaic Scrutiny:** The Pharisees were intensely concerned with ritual washings and ceremonial authority, viewing John's baptism as an unauthorized ritual innovation.",
        ],
    },
    25: {
        "tags": ["theme/prophecy", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "ezekiel-36-25", "note": "Then will I sprinkle clean water upon you, and ye shall be clean"},
            {"type": "xref/parallel", "target": "zechariah-13-1", "note": "In that day there shall be a fountain opened to the house of David... for sin and for uncleanness"},
        ],
        "correlations": [
            "*   Theme: The authority to baptize covenant Jews as a sign of repentance",
            "*   OT Background: Ezekiel 36:25; Zechariah 13:1",
            "*   Spirit of Prophecy: The Desire of Ages, p. 135",
        ],
        "notes": [
            "*   **Challenge to Baptismal Authority:** Proselyte baptism was practiced for Gentiles entering Judaism; but John was baptizing covenant Jews, implying that even the seed of Abraham needed spiritual cleansing before Messiah's arrival.",
        ],
    },
    26: {
        "tags": ["theme/christ", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-11", "note": "I indeed baptize you with water unto repentance"},
            {"type": "xref/parallel", "target": "luke-3-16", "note": "John answered, saying unto them all, I indeed baptize you with water"},
            {"type": "xref/parallel", "target": "acts-1-5", "note": "For John truly baptized with water; but ye shall be baptized with the Holy Ghost"},
        ],
        "correlations": [
            "*   Theme: Water baptism versus the unseen presence of the Messiah",
            "*   NT Parallels: Acts 11:16; 19:4",
            "*   Spirit of Prophecy: The Desire of Ages, p. 135 — There standeth one among you, whom ye know not",
        ],
        "notes": [
            "*   **The Unrecognized Majesty (*meson hymon hesteken*, G3319 G2476):** Christ was already present in the crowd, mingling unrecognized among the common people — an enduring symbol of His condescension.",
        ],
    },
    27: {
        "tags": ["theme/christ", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-11", "note": "Whose shoes I am not worthy to bear"},
            {"type": "xref/parallel", "target": "mark-1-7", "note": "The latchet of whose shoes I am not worthy to stoop down and unloose"},
            {"type": "xref/parallel", "target": "luke-3-16", "note": "The latchet of whose shoes I am not worthy to unloose"},
            {"type": "xref/parallel", "target": "acts-13-25", "note": "Whose shoes of his feet I am not worthy to loose"},
        ],
        "correlations": [
            "*   Theme: Supreme humility before the exalted Christ",
            "*   Spirit of Prophecy: The Desire of Ages, p. 135",
        ],
        "notes": [
            "*   **Untying the Sandal Strap:** In Jewish custom, unbinding a master's sandals was a duty reserved for the lowest household slaves, which Hebrew disciples were not required to perform for their rabbis. John deemed himself unworthy of even this lowest menial service before Jesus.",
        ],
    },
    28: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-3-26", "note": "He that was with thee beyond Jordan, to whom thou barest witness"},
            {"type": "xref/parallel", "target": "john-10-40", "note": "And went away again beyond Jordan into the place where John at first baptized"},
        ],
        "correlations": [
            "*   Theme: Historical and geographical setting of John's ministry",
            "*   Spirit of Prophecy: The Desire of Ages, p. 132",
        ],
        "notes": [
            "*   **Bethabara / Bethany Beyond Jordan:** The geographical marker confirms the eyewitness historical foundation of John's Gospel, situated on the eastern side of the Jordan river.",
        ],
    },
    29: {
        "tags": ["theme/sanctuary", "theme/christ", "theme/typology", "theme/redemption"],
        "xrefs": [
            {"type": "xref/theme", "target": "exodus-12-3-13", "note": "Your lamb shall be without blemish — the Passover lamb typology"},
            {"type": "xref/theme", "target": "isaiah-53-7", "note": "He is brought as a lamb to the slaughter, and as a sheep before her shearers is dumb"},
            {"type": "xref/parallel", "target": "1-corinthians-5-7", "note": "For even Christ our passover is sacrificed for us"},
            {"type": "xref/parallel", "target": "1-peter-1-18-19", "note": "Redeemed with the precious blood of Christ, as of a lamb without blemish"},
            {"type": "xref/theme", "target": "revelation-5-6-12", "note": "A Lamb as it had been slain... Worthy is the Lamb that was slain"},
            {"type": "xref/spirit-prophecy", "target": "des-11-1", "note": "The Desire of Ages, Chapter 11 — 'The Baptism'"},
        ],
        "correlations": [
            "*   Theme: The Lamb of God (*Amnos tou Theou*) and Universal Atonement",
            "*   OT Sanctuary Anchor: Exodus 12:3-13 (Passover Lamb); Exodus 29:38-42 (Daily Tamid); Leviticus 4 (Sin Offering); Isaiah 53:7",
            "*   NT Parallels: Acts 8:32; Hebrews 9:26; 1 John 2:2; Revelation 13:8",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 136-137 — The sanctuary service pointed to the Lamb of God",
        ],
        "notes": [
            "*   **Behold the Lamb of God (*Ide ho amnos tou Theou*, G2396 G286 G3588 G2316):** The culmination of the entire Levitical sacrificial economy. The daily morning and evening sacrifices, the Passover lamb, and the suffering servant of Isaiah 53:7 coalesce in Jesus of Nazareth.",
            "*   **Taking Away the Sin of the World (*ho airoon ten hamartian tou kosmou*, G142 G266):** The present participle *airoon* indicates continuous, comprehensive expiation: Christ lifts up and bears away the sin of the entire world, making atonement available to all humanity.",
        ],
    },
    30: {
        "tags": ["theme/christ", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-15", "note": "He that cometh after me is preferred before me: for he was before me"},
            {"type": "xref/parallel", "target": "john-1-27", "note": "He it is, who coming after me is preferred before me"},
        ],
        "correlations": [
            "*   Theme: The Baptist's public testimony pointing his hearers to Jesus",
            "*   Spirit of Prophecy: The Desire of Ages, p. 137",
        ],
        "notes": [
            "*   **Public Pointing:** John reiterates his testimony in the immediate physical presence of Jesus, directing the eyes of all Israel to their Messiah.",
        ],
    },
    31: {
        "tags": ["theme/prophecy", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "luke-1-80", "note": "And the child grew... and was in the deserts till the day of his shewing unto Israel"},
            {"type": "xref/parallel", "target": "john-1-33", "note": "And I knew him not: but he that sent me to baptize with water, the same said unto me"},
        ],
        "correlations": [
            "*   Theme: The manifestation of the Messiah to Israel as the primary purpose of John's baptism",
            "*   Spirit of Prophecy: The Desire of Ages, p. 137",
        ],
        "notes": [
            "*   **Manifested to Israel (*phanerothei to Israeli*, G5319):** John did not know Jesus as the verified Messiah through personal acquaintance or kinship, but waited for the divine sign promised by God.",
        ],
    },
    32: {
        "tags": ["theme/holy-spirit", "theme/christ", "theme/sanctuary"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-16", "note": "And Jesus, when he was baptized, went up straightway out of the water: and, lo, the heavens were opened unto him, and he saw the Spirit of God descending like a dove"},
            {"type": "xref/parallel", "target": "mark-1-10", "note": "And straightway coming up out of the water, he saw the heavens opened, and the Spirit like a dove descending upon him"},
            {"type": "xref/parallel", "target": "luke-3-22", "note": "And the Holy Ghost descended in a bodily shape like a dove upon him"},
            {"type": "xref/spirit-prophecy", "target": "des-11-1", "note": "The Desire of Ages, Chapter 11 — 'The Baptism'"},
        ],
        "correlations": [
            "*   Theme: The descent of the Holy Spirit at Jesus' baptism and the anointing of the Messiah",
            "*   OT Background: Genesis 1:2; 8:8-12; Isaiah 11:2; 61:1",
            "*   NT Parallels: Acts 10:38",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 111-113 — The dove as an emblem of purity and peace",
        ],
        "notes": [
            "*   **The Heavenly Sign (*etheasamēn to Pneuma*, G2300 G4151):** John bore solemn record that he saw the Holy Spirit descend from heaven like a dove and remain (*emeinen*, G3306) upon Him. Unlike temporary prophetic anointings in the OT, the Spirit permanently abides upon Christ without measure (John 3:34).",
        ],
    },
    33: {
        "tags": ["theme/holy-spirit", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-11", "note": "He shall baptize you with the Holy Ghost, and with fire"},
            {"type": "xref/parallel", "target": "acts-1-5", "note": "Ye shall be baptized with the Holy Ghost not many days hence"},
            {"type": "xref/parallel", "target": "acts-2-1-4", "note": "And they were all filled with the Holy Ghost"},
        ],
        "correlations": [
            "*   Theme: The Baptism of the Holy Spirit",
            "*   OT Background: Joel 2:28-29; Isaiah 44:3",
            "*   NT Parallels: 1 Corinthians 12:13; Titus 3:5-6",
            "*   Spirit of Prophecy: The Desire of Ages, p. 143",
        ],
        "notes": [
            "*   **Baptizer in the Holy Spirit (*ho baptizoon en Pneumati Hagio*):** Water baptism symbolized outward repentance; Christ's baptism in the Holy Spirit imparts internal regeneration, divine power, and eternal life.",
        ],
    },
    34: {
        "tags": ["theme/christ", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-3-17", "note": "And lo a voice from heaven, saying, This is my beloved Son, in whom I am well pleased"},
            {"type": "xref/parallel", "target": "john-1-49", "note": "Nathanael answered and saith unto him, Rabbi, thou art the Son of God"},
            {"type": "xref/parallel", "target": "john-20-31", "note": "These are written, that ye might believe that Jesus is the Christ, the Son of God"},
        ],
        "correlations": [
            "*   Theme: The apostolic and prophetic confession: Jesus is the Son of God",
            "*   OT Background: Psalm 2:7; 2 Samuel 7:14",
            "*   NT Parallels: Matthew 16:16; Acts 9:20; 1 John 4:15",
            "*   Spirit of Prophecy: The Desire of Ages, p. 113",
        ],
        "notes": [
            "*   **The Definitive Verdict (*houtos estin ho Huios tou Theou*):** John concludes his testimony with the supreme Christological confession: 'This is the Son of God.' This forms the thematic arch connecting the prologue (1:14, 18) to the conclusion of the Gospel (20:31).",
        ],
    },
    35: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-29", "note": "The next day John seeth Jesus coming unto him"},
            {"type": "xref/parallel", "target": "john-1-37", "note": "And the two disciples heard him speak, and they followed Jesus"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: The transition of disciples from the forerunner to the Master",
            "*   Spirit of Prophecy: The Desire of Ages, p. 138",
        ],
        "notes": [
            "*   **The Faithful Mentor:** John stands with two of his disciples (Andrew and likely John the Evangelist himself), preparing to transfer their allegiance to Christ.",
        ],
    },
    36: {
        "tags": ["theme/sanctuary", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-29", "note": "Behold the Lamb of God, which taketh away the sin of the world"},
            {"type": "xref/parallel", "target": "revelation-5-6", "note": "In the midst of the throne... stood a Lamb as it had been slain"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Looking steadfastly upon the Lamb of God",
            "*   Spirit of Prophecy: The Desire of Ages, p. 138",
        ],
        "notes": [
            "*   **Looking Steadfastly (*emblepsas*, G1689):** John fixed his gaze intently upon Jesus as He walked by, repeating the sacred watchword: 'Behold the Lamb of God!'",
        ],
    },
    37: {
        "tags": ["theme/faith", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-4-19-20", "note": "Follow me, and I will make you fishers of men. And they straightway left their nets, and followed him"},
            {"type": "xref/parallel", "target": "john-1-43", "note": "Jesus saith unto him, Follow me"},
        ],
        "correlations": [
            "*   Theme: The prompt obedience of the first disciples",
            "*   Spirit of Prophecy: The Desire of Ages, p. 138",
        ],
        "notes": [
            "*   **Following Jesus (*ekolouthesan to Iesou*):** Hearing the Baptist's witness, the two disciples immediately left their teacher to follow Jesus. This marks the inception of the Christian church.",
        ],
    },
    38: {
        "tags": ["theme/faith", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-7-7", "note": "Ask, and it shall be given you; seek, and ye shall find"},
            {"type": "xref/parallel", "target": "john-20-15", "note": "Jesus saith unto her, Woman, why weepest thou? whom seekest thou?"},
        ],
        "correlations": [
            "*   Theme: Christ's penetrating question to seekers: 'What seek ye?'",
            "*   Spirit of Prophecy: The Desire of Ages, p. 139",
        ],
        "notes": [
            "*   **The First Words of Jesus in John's Gospel:** 'What seek ye?' (*Ti zeteite;*) Christ probes their motives, inviting them to examine the deepest desires of their hearts. They respond by seeking communion with Him: 'Master, where dwellest thou?'",
        ],
    },
    39: {
        "tags": ["theme/faith", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-1-46", "note": "Philip saith unto him, Come and see"},
            {"type": "xref/parallel", "target": "revelation-22-17", "note": "And the Spirit and the bride say, Come. And let him that heareth say, Come"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: The gracious invitation of Christ: 'Come and see'",
            "*   Spirit of Prophecy: The Desire of Ages, p. 139 — An afternoon of sacred communion with Jesus",
        ],
        "notes": [
            "*   **Come and See (*Erchesthe kai idete*):** Christianity is experiential. Faith is not validated by abstract speculation, but by personal encounter with Christ. They came, saw where He dwelt, and spent the remainder of the day in sacred fellowship.",
        ],
    },
    40: {
        "tags": ["theme/prophecy", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-4-18", "note": "And Jesus, walking by the sea of Galilee, saw two brethren, Simon called Peter, and Andrew his brother"},
            {"type": "xref/parallel", "target": "john-6-8", "note": "One of his disciples, Andrew, Simon Peter's brother"},
        ],
        "correlations": [
            "*   Theme: Andrew identified as one of the two foundational seekers",
            "*   Spirit of Prophecy: The Desire of Ages, p. 139",
        ],
        "notes": [
            "*   **Andrew's Ministry:** Andrew is consistently portrayed in John's Gospel as the disciple who brings individuals to Jesus (Simon Peter in 1:41, the boy with loaves in 6:8, and the Greeks in 12:22).",
        ],
    },
    41: {
        "tags": ["theme/prophecy", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "daniel-9-25-26", "note": "Know therefore and understand, that from the going forth of the commandment... unto the Messiah the Prince"},
            {"type": "xref/parallel", "target": "john-4-25", "note": "The woman saith unto him, I know that Messias cometh, which is called Christ"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Personal evangelism and the discovery of the Messiah",
            "*   OT Background: Daniel 9:25-26; Psalm 2:2",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 139-141",
        ],
        "notes": [
            "*   **We Have Found the Messias (*Heurekamen ton Messian*):** Andrew's immediate impulse upon encountering Jesus was to find his own brother Simon. Personal discovery of Christ naturally overflows into missionary zeal.",
        ],
    },
    42: {
        "tags": ["theme/prophecy", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-16-18", "note": "Thou art Peter, and upon this rock I will build my church"},
            {"type": "xref/parallel", "target": "1-peter-2-4-5", "note": "Ye also, as lively stones, are built up a spiritual house"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Christ's prophetic renaming of Simon to Cephas (Peter)",
            "*   OT Background: Genesis 17:5 (Abram to Abraham); Genesis 32:28 (Jacob to Israel)",
            "*   NT Parallels: Mark 3:16; Luke 6:14",
            "*   Spirit of Prophecy: The Desire of Ages, p. 139 — Christ read Peter's character and future transformation",
        ],
        "notes": [
            "*   **Thou Shalt Be Called Cephas (*sy klethese Kephas*):** Aramaic *Kepha* / Greek *Petros* ('a stone / rolling rock'). Jesus looked into Simon's impulsive, unsteady nature and saw the transformed, steadfast witness he would become through divine grace.",
        ],
    },
    43: {
        "tags": ["theme/sanctification", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-8-22", "note": "Follow me; and let the dead bury their dead"},
            {"type": "xref/parallel", "target": "john-12-26", "note": "If any man serve me, let him follow me"},
            {"type": "xref/parallel", "target": "john-21-22", "note": "Follow thou me"},
        ],
        "correlations": [
            "*   Theme: The sovereign call of Jesus: 'Follow me'",
            "*   Spirit of Prophecy: The Desire of Ages, p. 140",
        ],
        "notes": [
            "*   **The Sovereign Summons (*Akolouthei moi*):** Jesus initiates the journey to Galilee and directly issues His call to Philip. The call to discipleship is an invitation into total life allegiance.",
        ],
    },
    44: {
        "tags": ["theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-11-21", "note": "Woe unto thee, Chorazin! woe unto thee, Bethsaida!"},
            {"type": "xref/parallel", "target": "john-12-21", "note": "The same came therefore to Philip, which was of Bethsaida of Galilee"},
        ],
        "correlations": [
            "*   Theme: The Galilean hometown connection between Philip, Andrew, and Peter",
            "*   Spirit of Prophecy: The Desire of Ages, p. 140",
        ],
        "notes": [
            "*   **Bethsaida of Galilee:** The shared hometown created natural community bonds which the Holy Spirit leveraged for the expansion of the kingdom.",
        ],
    },
    45: {
        "tags": ["theme/prophecy", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "genesis-3-15", "note": "The seed of the woman that shall bruise the serpent's head"},
            {"type": "xref/parallel", "target": "genesis-49-10", "note": "The sceptre shall not depart from Judah... until Shiloh come"},
            {"type": "xref/parallel", "target": "deuteronomy-18-18", "note": "I will raise them up a Prophet from among their brethren"},
            {"type": "xref/parallel", "target": "luke-24-27", "note": "And beginning at Moses and all the prophets, he expounded unto them in all the scriptures the things concerning himself"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Jesus as the fulfillment of the Law of Moses and the Prophets",
            "*   OT Background: Genesis 3:15; 22:18; 49:10; Deuteronomy 18:15; Isaiah 7:14; 9:6; 53",
            "*   NT Parallels: Acts 26:22; 28:23; Romans 1:2-3",
            "*   Spirit of Prophecy: The Desire of Ages, p. 140",
        ],
        "notes": [
            "*   **Of Whom Moses and the Prophets Did Write:** Philip recognizes that Jesus fulfills the entire Old Testament canonical canon — the Pentateuch (*nomos*) and the prophetic books (*prophetai*).",
        ],
    },
    46: {
        "tags": ["theme/faith", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-7-41-42", "note": "Shall Christ come out of Galilee? Hath not the scripture said, That Christ cometh of the seed of David, and out of the town of Bethlehem?"},
            {"type": "xref/parallel", "target": "john-7-52", "note": "Search, and look: for out of Galilee ariseth no prophet"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Overcoming regional prejudice through personal inspection ('Come and see')",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 140-141 — Philip did not argue; he said, 'Come and see'",
        ],
        "notes": [
            "*   **Prejudice Overcome by Experience:** Nathanael voiced the popular disdain toward the obscure village of Nazareth. Philip did not engage in theological debate, but gave the simplest, most powerful invitation: 'Come and see.'",
        ],
    },
    47: {
        "tags": ["theme/christ", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalms-32-2", "note": "Blessed is the man unto whom the LORD imputeth not iniquity, and in whose spirit there is no guile"},
            {"type": "xref/parallel", "target": "romans-2-28-29", "note": "He is not a Jew, which is one outwardly... he is a Jew, which is one inwardly"},
            {"type": "xref/parallel", "target": "revelation-14-5", "note": "And in their mouth was found no guile: for they are without fault before the throne of God"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: An Israelite in whom is no guile (*dolos*) — Jacob redeemed",
            "*   OT Background: Genesis 27:35; 32:28; Psalm 32:2",
            "*   NT Parallels: 1 Peter 2:22; Revelation 14:5",
            "*   Spirit of Prophecy: The Desire of Ages, p. 141",
        ],
        "notes": [
            "*   **An Israelite Indeed, in Whom is No Guile (*en ho dolos ouk estin*):** Jacob's original name meant 'supplanter / deceiver' (*guile*). When God conquered him at Jabbok, he became *Israel* — a prince with God. Jesus honors Nathanael as a true child of the transformed Jacob, free from hypocrisy.",
        ],
    },
    48: {
        "tags": ["theme/christ", "theme/prayer"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalms-139-1-4", "note": "O LORD, thou hast searched me, and known me. Thou knowest my downsitting and mine uprising"},
            {"type": "xref/parallel", "target": "john-2-24-25", "note": "He knew all men, and needed not that any should testify of man: for he knew what was in man"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Divine omniscience and secret prayer under the fig tree",
            "*   OT Background: 1 Kings 4:25; Micah 4:4; Psalm 139:1-12",
            "*   Spirit of Prophecy: The Desire of Ages, p. 141 — Under the fig tree Nathanael had prayed to know whether Jesus was the Messiah",
        ],
        "notes": [
            "*   **Under the Fig Tree (*hypo ten syken*):** In Jewish tradition, the shade of the fig tree was a favored place for prayer, meditation, and Torah study. Nathanael had poured out his heart in secret, asking for divine light regarding the Messiah. Jesus' disclosure proved His divine omniscience.",
        ],
    },
    49: {
        "tags": ["theme/christ", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalms-2-7", "note": "The LORD hath said unto me, Thou art my Son; this day have I begotten thee"},
            {"type": "xref/parallel", "target": "matthew-14-33", "note": "Of a truth thou art the Son of God"},
            {"type": "xref/parallel", "target": "john-1-34", "note": "And I saw, and bare record that this is the Son of God"},
        ],
        "correlations": [
            "*   Theme: Nathanael's triumphant confession: Son of God and King of Israel",
            "*   OT Background: Psalm 2:6-7; Zephaniah 3:15",
            "*   NT Parallels: Matthew 16:16; John 12:13",
            "*   Spirit of Prophecy: The Desire of Ages, p. 141",
        ],
        "notes": [
            "*   **The Royal and Divine Confession:** Nathanael combines the divine title (*Son of God*, expressing deity) with the messianic royal title (*King of Israel*, expressing covenant sovereignty over the redeemed).",
        ],
    },
    50: {
        "tags": ["theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-11-40", "note": "Said I not unto thee, that, if thou wouldest believe, thou shouldest see the glory of God?"},
            {"type": "xref/parallel", "target": "john-14-12", "note": "He that believeth on me, the works that I do shall he do also; and greater works than these shall he do"},
        ],
        "correlations": [
            "*   Theme: Faith rewarded with expanding revelations of divine glory",
            "*   Spirit of Prophecy: The Desire of Ages, p. 142",
        ],
        "notes": [
            "*   **Greater Things Shalt Thou See (*meizo touton opsei*):** Sincere initial faith is the doorway to progressive spiritual sight. Christ promises that Nathanael's quick surrender to truth will be rewarded with majestic cosmic visions.",
        ],
    },
    51: {
        "tags": ["theme/christ", "theme/typology", "theme/sanctuary"],
        "xrefs": [
            {"type": "xref/theme", "target": "genesis-28-12", "note": "And he dreamed, and behold a ladder set up on the earth, and the top of it reached to heaven: and behold the angels of God ascending and descending on it — Jacob's ladder typology"},
            {"type": "xref/parallel", "target": "daniel-7-13", "note": "Behold, one like the Son of man came with the clouds of heaven"},
            {"type": "xref/parallel", "target": "matthew-26-64", "note": "Hereafter shall ye see the Son of man sitting on the right hand of power"},
            {"type": "xref/parallel", "target": "hebrews-1-14", "note": "Are they not all ministering spirits, sent forth to minister for them who shall be heirs of salvation?"},
            {"type": "xref/spirit-prophecy", "target": "des-14-1", "note": "The Desire of Ages, Chapter 14 — 'We Have Found the Messias'"},
        ],
        "correlations": [
            "*   Theme: Jesus the True Jacob's Ladder linking Heaven and Earth",
            "*   OT Typology Anchor: Genesis 28:12 (Jacob's Ladder at Bethel); Daniel 7:13 (*Bar Enash* / Son of Man)",
            "*   NT Parallels: 1 Timothy 2:5 (One Mediator); Hebrews 10:19-20",
            "*   Spirit of Prophecy: Patriarchs and Prophets, p. 184; The Desire of Ages, pp. 142-143 — Christ the bridge spanning the gulf made by sin",
        ],
        "notes": [
            "*   **The True Jacob's Ladder (*Gen 28:12* Typology):** In Genesis 28, the fugitive Jacob saw a mystic ladder resting on the earth while its top touched heaven, with angels ascending and descending upon it. Jesus declares Himself to be that living ladder: His humanity rests on the earth, while His divinity reaches the throne of God.",
            "*   **The Son of Man (*ho Huios tou anthropou*, G5207 G444):** First appearance of Jesus' favorite self-designation in John's Gospel. Rooted in Daniel 7:13, it highlights both His solidarity with suffering humanity and His ultimate heavenly sovereignty.",
            "*   **Spanning the Abyss of Sin:** Sin severed communion between earth and heaven. In Christ, open heaven (*ouranon aneogota*) is restored, and angelic ministry flows unhindered between God and humanity.",
        ],
    },
}


def curate_verse(v_num: int) -> bool:
    path = JOHN1_DIR / f"john-1-{v_num}-kjv.md"
    if not path.exists():
        print(f"Error: {path} does not exist")
        return False

    content = path.read_text(encoding="utf-8")
    curation = JOHN1_CURATION.get(v_num)
    if not curation:
        print(f"Warning: No curation data for John 1:{v_num}")
        return False

    # 1. Update frontmatter
    # Replace status: draft with status: review in frontmatter and source notes
    content = re.sub(r"^status:\s*draft", "status: review", content, flags=re.MULTILINE)
    content = content.replace(
        "- Status: draft. Deterministic skeleton only — cross-references and\n  theological notes await human curation per CONTRIBUTION_STANDARDS.md.",
        "- Status: review. Cross-references, correlations, and study notes curated per CONTRIBUTION_STANDARDS.md.",
    )
    # Replace updated date
    content = re.sub(r"^updated:\s*\d{4}-\d{2}-\d{2}", f"updated: {CURATION_DATE}", content, flags=re.MULTILINE)

    # Add extra tags to frontmatter tags in single batch operation:
    missing_tags = [t for t in dict.fromkeys(curation.get("tags", [])) if f"- {t}" not in content]
    if missing_tags:
        tag_lines = "".join(f"  - {t}\n" for t in missing_tags)
        content = content.replace("tags:\n", f"tags:\n{tag_lines}", 1)

    # Insert cross_references: block before closing frontmatter ---
    xrefs = curation.get("xrefs", [])
    if xrefs and "cross_references:" not in content:
        xref_lines = ["cross_references:"]
        for x in xrefs:
            xref_lines.append(f"  - type: {x['type']}")
            xref_lines.append(f"    target: \"{x['target']}\"")
            note_escaped = x['note'].replace('"', '\\"')
            xref_lines.append(f"    note: \"{note_escaped}\"")
        xref_block = "\n".join(xref_lines) + "\n"
        content = re.sub(r"\n---\n", f"\n{xref_block}---\n", content, count=1)

    # 2. Add Correlations and Study Notes before ## Source Notes
    correlations = curation.get("correlations", [])
    notes = curation.get("notes", [])

    body_sections = []
    if correlations:
        body_sections.append("## Correlations\n\n" + "\n".join(correlations) + "\n")
    if notes:
        body_sections.append("## Study Notes\n\n<!-- AI-GENERATED -->\n" + "\n".join(notes) + "\n<!-- END AI-GENERATED -->\n")

    if body_sections and "## Correlations" not in content and "## Study Notes" not in content:
        insert_text = "\n" + "\n".join(body_sections)
        content = content.replace("\n## Source Notes\n", f"{insert_text}\n## Source Notes\n")

    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    curated_count = 0
    for v in range(1, 52):
        if curate_verse(v):
            curated_count += 1
    print(f"Successfully curated {curated_count}/51 verses in John 1")
    return 0


if __name__ == "__main__":
    main()
