"""curate_john17.py — Script to curate John 17 (all 26 verses) for Pillar A3.

Moves John 17 entries from draft to status: review, adding rich cross-references,
theological correlations, and verified study notes while preserving the
deterministic KJV verse text, Strong's tags, and Greek word studies verbatim.
"""

from __future__ import annotations

import re
from pathlib import Path

# Curation date
CURATION_DATE = "2026-09-06"

REPO_ROOT = Path(__file__).resolve().parent.parent
JOHN17_DIR = REPO_ROOT / "materials/bible/nt/john/17"

# Comprehensive theological curation data for John 17 (26 verses)
JOHN17_CURATION: dict[int, dict] = {
    1: {
        "tags": ["theme/christ", "theme/prayer", "theme/sanctuary"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-12-23", "note": "Jesus answered them, saying, The hour is come, that the Son of man should be glorified"},
            {"type": "xref/parallel", "target": "john-13-31-32", "note": "Now is the Son of man glorified, and God is glorified in him"},
            {"type": "xref/parallel", "target": "philippians-2-9-11", "note": "Wherefore God also hath highly exalted him, and given him a name which is above every name"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The High Priestly invocation and the hour of ultimate glorification",
            "*   OT Background: Leviticus 16:11-17 — The high priest making atonement before the Lord",
            "*   NT Parallels: Matthew 26:39; John 7:30; 8:20; 12:23, 27; Hebrews 5:7",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 675-680 — Christ entering upon His priestly intercession",
        ],
        "notes": [
            "*   **The Appointed Hour (*Elēlythen he hōra*, G2064 G5610):** Throughout John's Gospel, Jesus repeatedly noted that 'mine hour is not yet come' (John 2:4; 7:30; 8:20). Here, at the threshold of Gethsemane and Calvary, the prophetic countdown culminates. The hour of redemption has arrived.",
            "*   **Mutual Glorification (*Doxason sou ton Huion*, G1392 G5207):** In Johannine theology, glory (*doxa*) is supremely manifested in self-sacrificing love upon the cross. The Son asks to be sustained through His passion so that His self-giving sacrifice might vindicate the character of the Father before the watching universe.",
            "*   **Sanctuary High Priestly Posture:** Having concluded His farewell discourse in the upper room, Jesus lifts His eyes to heaven as the great High Priest. Before shedding His own blood, He offers solemn intercession for His house and covenant people, fulfilling the typological pattern of the Day of Atonement.",
        ],
    },
    2: {
        "tags": ["theme/christ", "theme/redemption", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-28-18", "note": "All power is given unto me in heaven and in earth"},
            {"type": "xref/parallel", "target": "john-5-21-27", "note": "For as the Father raiseth up the dead, and quickeneth them; even so the Son quickeneth whom he will"},
            {"type": "xref/parallel", "target": "john-6-37-40", "note": "All that the Father giveth me shall come to me; and him that cometh to me I will in no wise cast out"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Divine sovereignty, universal authority, and the gift of eternal life",
            "*   OT Background: Daniel 7:13-14 — Dominion, glory, and a kingdom given to the Son of Man",
            "*   NT Parallels: Matthew 11:27; John 3:35; 10:28; Romans 14:9; 1 Corinthians 15:27",
            "*   Spirit of Prophecy: Patriarchs and Prophets, p. 63 — The covenant of grace established from eternity",
        ],
        "notes": [
            "*   **Universal Authority (*Exousian pasēs sarkos*, G1849 G3956 G4561):** The Father has granted the incarnate Son jurisdiction over 'all flesh' (all humanity). This universal dominion is exercised not for coercive subjugation, but to bestow eternal life upon the covenant community.",
            "*   **The Bestowal of Eternal Life (*Dōsei autois zōēn aiōnion*, G1325 G846 G2222 G166):** Eternal life is not an abstract concept or mere unending duration; it is the divine, unborrowed life of God mediated exclusively through Christ to fallen humanity.",
        ],
    },
    3: {
        "tags": ["theme/christ", "theme/faith", "theme/redemption"],
        "xrefs": [
            {"type": "xref/parallel", "target": "jeremiah-9-23-24", "note": "Let him that glorieth glory in this, that he understandeth and knoweth me"},
            {"type": "xref/parallel", "target": "john-1-18-kjv", "note": "No man hath seen God at any time; the only begotten Son... he hath declared him"},
            {"type": "xref/parallel", "target": "1-john-5-20", "note": "And we know that the Son of God is come, and hath given us an understanding, that we may know him that is true"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Experiential knowledge of the true God and Jesus Christ as eternal life",
            "*   OT Background: Exodus 34:6-7; Jeremiah 9:23-24; Hosea 6:3, 6",
            "*   NT Parallels: Philippians 3:8-10; 2 Peter 1:2-3; 1 John 5:20",
            "*   Spirit of Prophecy: The Desire of Ages, p. 762 — To know God is to love Him",
        ],
        "notes": [
            "*   **Experiential Knowledge (*Ginōskōsin*, G1097):** *Ginosko* mirrors the Hebrew *yada*, signifying intimate, transformational communion rather than mere theoretical comprehension. True knowledge of God involves walking in harmony with His character of self-sacrificing love.",
            "*   **The Only True God and the Sent Messiah (*Ton monon alēthinon Theon kai... Iēsoun Christon*, G3441 G228 G2316 G2424 G5547):** The Father is the fountainhead of divinity (*alethinos* = genuine, ultimate reality), and Jesus Christ is His definitive, equal apostle and mediator (*hon apesteilas*). Eternal life is inseparable from fellowship with both.",
        ],
    },
    4: {
        "tags": ["theme/christ", "theme/redemption", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-4-34", "note": "My meat is to do the will of him that sent me, and to finish his work"},
            {"type": "xref/parallel", "target": "john-5-36", "note": "The works which the Father hath given me to finish... bear witness of me"},
            {"type": "xref/parallel", "target": "john-19-30", "note": "When Jesus therefore had received the vinegar, he said, It is finished"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The finished earthly mission and the vindication of divine love",
            "*   OT Background: Isaiah 42:1-4; 53:10-11 — The servant prospering in the Lord's pleasure",
            "*   NT Parallels: Acts 20:24; 2 Timothy 4:7; Hebrews 12:2",
            "*   Spirit of Prophecy: The Desire of Ages, p. 675 — Christ had completed the revelation of God's character",
        ],
        "notes": [
            "*   **The Finished Work (*To ergon teleiōsas*, G2041 G5048):** In anticipatory triumph, Jesus speaks of His earthly work as an accomplished totality. By a life of sinless obedience, tender compassion, and unspotted holiness, He has fully unveiled the Father and unmasked the deceptions of the adversary.",
        ],
    },
    5: {
        "tags": ["theme/christ", "theme/origins", "theme/covenant"],
        "xrefs": [
            {"type": "xref/theme", "target": "john-1-1-kjv", "note": "In the beginning was the Word, and the Word was with God, and the Word was God"},
            {"type": "xref/parallel", "target": "philippians-2-6", "note": "Who, being in the form of God, thought it not robbery to be equal with God"},
            {"type": "xref/parallel", "target": "colossians-1-17", "note": "And he is before all things, and by him all things consist"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Restoration of pre-existent, unoriginated glory beside the Father",
            "*   OT Background: Proverbs 8:22-30; Micah 5:2 — Whose goings forth have been from of old, from everlasting",
            "*   NT Parallels: John 1:1-3; Philippians 2:5-11; Hebrews 1:3",
            "*   Spirit of Prophecy: The Desire of Ages, p. 23 — From the days of eternity the Lord Jesus Christ was one with the Father",
        ],
        "notes": [
            "*   **Pre-Existent Fellowship (*Para seautō... para soi*, G3844 G4572 G4771):** Christ prays to resume the visible divine glory He shared alongside the Father before the foundation of spacetime (*pro tou ton kosmon einai*). He laid this glory aside in the Incarnation, veiled in human flesh, but never forfeited His uncreated deity.",
        ],
    },
    6: {
        "tags": ["theme/faith", "theme/covenant", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalm-22-22", "note": "I will declare thy name unto my brethren: in the midst of the congregation will I praise thee"},
            {"type": "xref/parallel", "target": "john-1-18-kjv", "note": "The only begotten Son... he hath declared him"},
            {"type": "xref/parallel", "target": "john-17-26-kjv", "note": "And I have declared unto them thy name, and will declare it"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Manifestation of the divine character and the obedience of faith",
            "*   OT Background: Exodus 3:13-15; 34:5-7 — Proclaiming the Name of YHWH",
            "*   NT Parallels: Hebrews 2:12; 1 John 2:3-5; Revelation 3:8",
            "*   Spirit of Prophecy: The Desire of Ages, p. 676 — The Name represents the merciful character of God",
        ],
        "notes": [
            "*   **Manifesting the Name (*Ephanerōsa sou to onoma*, G5319 G3686):** In biblical thought, the 'name' denotes the moral essence, character, and covenant authority of the person. Christ did not merely pronounce the letters of God's name; He visibly lived out the holiness, love, and justice of the Father before His disciples.",
            "*   **Keeping the Word (*Ton logon sou tetērēkasin*, G3056 G5083):** Despite their weaknesses and perplexities, the disciples held fast to the divine revelation, recognizing Christ's words as eternal truth.",
        ],
    },
    7: {
        "tags": ["theme/faith", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-7-16-17", "note": "My doctrine is not mine, but his that sent me"},
            {"type": "xref/parallel", "target": "john-8-28", "note": "As my Father hath taught me, I speak these things"},
            {"type": "xref/parallel", "target": "john-12-49", "note": "For I have not spoken of myself; but the Father which sent me, he gave me a commandment"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The disciples' spiritual comprehension of Christ's divine mission",
            "*   OT Background: Deuteronomy 18:18 — I will put my words in his mouth",
            "*   NT Parallels: Matthew 16:16-17; John 16:30",
            "*   Spirit of Prophecy: The Desire of Ages, p. 676",
        ],
        "notes": [
            "*   **Divine Origin Acknowledged (*Para sou estin*, G3844 G4771 G1510):** The disciples grasped the fundamental reality that everything Christ possesses—His words, powers, authority, and love—originates in unbroken communion with the Father.",
        ],
    },
    8: {
        "tags": ["theme/faith", "theme/christ", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "deuteronomy-18-18", "note": "And he shall speak unto them all that I shall command him"},
            {"type": "xref/parallel", "target": "john-6-68-69", "note": "Lord, to whom shall we go? thou hast the words of eternal life"},
            {"type": "xref/parallel", "target": "john-16-27-30", "note": "For the Father himself loveth you, because ye have loved me, and have believed that I came out from God"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Receiving the apostolic revelation and believing the divine sending",
            "*   OT Background: Isaiah 50:4 — The Lord GOD hath given me the tongue of the learned",
            "*   NT Parallels: 1 Thessalonians 2:13; 1 John 4:14",
            "*   Spirit of Prophecy: The Desire of Ages, p. 676",
        ],
        "notes": [
            "*   **Threefold Epistemology of Faith:** (1) Receiving the words (*elabon*); (2) Truly knowing Christ's eternal procession from God (*alēthōs egnōsan*); and (3) Believing the Father sent Him (*episteusan*). Christian faith rests upon objective historical revelation received into humble hearts.",
        ],
    },
    9: {
        "tags": ["theme/prayer", "theme/christ", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "luke-22-32", "note": "But I have prayed for thee, that thy faith fail not"},
            {"type": "xref/parallel", "target": "romans-8-34", "note": "It is Christ that died, yea rather, that is risen again, who is even at the right hand of God, who also maketh intercession for us"},
            {"type": "xref/parallel", "target": "hebrews-7-25", "note": "Wherefore he is able also to save them to the uttermost... seeing he ever liveth to make intercession for them"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The particularity and power of Christ's High Priestly intercession",
            "*   OT Background: Exodus 28:29 — Aaron bearing the names of the children of Israel in the breastplate of judgment",
            "*   NT Parallels: Hebrews 9:24; 1 John 2:1-2",
            "*   Spirit of Prophecy: The Desire of Ages, p. 676 — The intercession of Christ is the anchor of the church",
        ],
        "notes": [
            "*   **Priestly Intercession (*Egō peri autōn erōtō*, G1473 G4012 G846 G2065):** Christ clarifies that at this solemn juncture He prays specifically for His disciples, not for the unregenerate world. While He died for the whole world (John 3:16), His priestly mediation is dedicated to preserving and empowering the covenant flock through whom the gospel will be proclaimed to that world.",
        ],
    },
    10: {
        "tags": ["theme/christ", "theme/covenant", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-10-30", "note": "I and my Father are one"},
            {"type": "xref/parallel", "target": "john-16-15", "note": "All things that the Father hath are mine"},
            {"type": "xref/parallel", "target": "2-thessalonians-1-10-12", "note": "When he shall come to be glorified in his saints, and to be admired in all them that believe"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Mutual divine ownership and Christ glorified in His redeemed saints",
            "*   OT Background: 1 Chronicles 29:11-12; Ezekiel 18:4",
            "*   NT Parallels: 1 Corinthians 3:21-23; Galatians 2:20",
            "*   Spirit of Prophecy: The Desire of Ages, p. 676 — The fruit of grace reflecting the Master's image",
        ],
        "notes": [
            "*   **Reciprocal Divine Co-Possession (*Ta ema panta sa estin kai ta sa ema*):** No mere creature could utter these words without blasphemy. The Son claims complete, joint ownership with the Father of all creation and redemption.",
            "*   **Glorified in Them (*Dedoxasmai en autois*, G1392 G1722 G846):** The perfect passive indicates an enduring reality: Christ is reflected, honored, and glorified as His character is reproduced in transformed disciples.",
        ],
    },
    11: {
        "tags": ["theme/prayer", "theme/covenant", "theme/sanctification"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-10-28-30", "note": "Neither shall any man pluck them out of my hand. My Father, which gave them me, is greater than all"},
            {"type": "xref/parallel", "target": "john-17-21-23", "note": "That they all may be one; as thou, Father, art in me, and I in thee"},
            {"type": "xref/parallel", "target": "1-peter-1-5", "note": "Who are kept by the power of God through faith unto salvation"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The Holy Father's keeping power and organic covenant oneness",
            "*   OT Background: Numbers 6:24-26 — The LORD bless thee, and keep thee",
            "*   NT Parallels: Ephesians 4:3-6; Philippians 2:1-2; Jude 1:24",
            "*   Spirit of Prophecy: Testimonies for the Church, vol. 8, pp. 239-243 — The unity of the Spirit",
        ],
        "notes": [
            "*   **The Invocation 'Holy Father' (*Pater Hagie*, G3962 G40):** A uniquely reverent address emphasizing the absolute purity and moral perfection of the Godhead.",
            "*   **Preservation in the Name (*Tērēson autous en tō onomati sou*, G5083 G3686):** The disciples are shielded from apostasy by being enveloped in the covenant character, truth, and authority of God.",
            "*   **Trinitarian Blueprint for Unity (*Hina ōsin hen kathōs hēmeis*):** Church unity is not political consensus or organizational uniformity, but spiritual oneness modeled after the harmonious love, purpose, and essence of the Father and Son.",
        ],
    },
    12: {
        "tags": ["theme/prophecy", "theme/christ", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalm-41-9", "note": "Yea, mine own familiar friend, in whom I trusted... hath lifted up his heel against me"},
            {"type": "xref/parallel", "target": "john-6-70-71", "note": "Have not I chosen you twelve, and one of you is a devil? He spake of Judas Iscariot"},
            {"type": "xref/parallel", "target": "john-13-18", "note": "That the scripture may be fulfilled, He that eateth bread with me hath lifted up his heel against me"},
            {"type": "xref/parallel", "target": "2-thessalonians-2-3", "note": "That man of sin be revealed, the son of perdition"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Pastoral guardianship and the tragedy of the son of perdition",
            "*   OT Background: Psalm 41:9; 109:8 — Prophetic foreknowledge of treachery",
            "*   NT Parallels: Matthew 26:24; Acts 1:16-20",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 716-722 — The fall and fate of Judas",
        ],
        "notes": [
            "*   **Vigilant Guardianship (*Ephylaxa*, G5442):** Jesus guarded the disciples like a faithful shepherd watching over his sheep, preserving all who yielded their wills to Him.",
            "*   **The Son of Perdition (*Ho huios tēs apōleias*, G5207 G684):** Judas was not predestined to be lost by arbitrary decree; Christ labored tirelessly to save him. By persistent covert self-seeking and resistance to the Holy Spirit, Judas became the embodiment of willful ruin (*apoleia*).",
        ],
    },
    13: {
        "tags": ["theme/faith", "theme/hope", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-15-11", "note": "These things have I spoken unto you, that my joy might remain in you, and that your joy might be full"},
            {"type": "xref/parallel", "target": "john-16-22-24", "note": "Your heart shall rejoice, and your joy no man taketh from you"},
            {"type": "xref/parallel", "target": "1-john-1-4", "note": "And these things write we unto you, that your joy may be full"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Fullness of divine joy in the midst of a hostile world",
            "*   OT Background: Nehemiah 8:10 — The joy of the LORD is your strength; Isaiah 61:10",
            "*   NT Parallels: Galatians 5:22; Philippians 4:4; 1 Peter 1:8",
            "*   Spirit of Prophecy: The Desire of Ages, p. 677 — Joy springing from surrender to divine love",
        ],
        "notes": [
            "*   **Christ's Imparted Joy (*Ten charan tēn emēn peplērōmenēn*, G5479 G4137):** Not superficial worldly happiness, but the deep, unshakable joy of complete alignment with the Father's will, even in the shadow of the cross.",
        ],
    },
    14: {
        "tags": ["theme/sanctification", "theme/faith", "theme/satan"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-15-18-19", "note": "If the world hate you, ye know that it hated me before it hated you"},
            {"type": "xref/parallel", "target": "1-john-3-13", "note": "Marvel not, my brethren, if the world hate you"},
            {"type": "xref/parallel", "target": "james-4-4", "note": "The friendship of the world is enmity with God"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The inevitable conflict between the kingdom of God and the spirit of the world",
            "*   OT Background: Genesis 3:15 — Enmity between the seed of the woman and the seed of the serpent",
            "*   NT Parallels: Matthew 10:22; Romans 8:7; 2 Timothy 3:12",
            "*   Spirit of Prophecy: The Great Controversy, pp. 505-510 — The antagonism between truth and error",
        ],
        "notes": [
            "*   **The World's Enmity (*Ho kosmos emisēsen autous*, G2889 G3404):** When believers receive God's Word, their values, priorities, and character contrast so sharply with fallen human culture that worldly opposition is inevitable.",
            "*   **Not of the World (*Ouk eisin ek tou kosmou*):** The disciples' origin, allegiance, and destination are heavenly, mirroring Christ's own divine nature.",
        ],
    },
    15: {
        "tags": ["theme/prayer", "theme/sanctification", "theme/satan"],
        "xrefs": [
            {"type": "xref/parallel", "target": "matthew-6-13", "note": "Deliver us from evil: For thine is the kingdom, and the power, and the glory, for ever"},
            {"type": "xref/parallel", "target": "2-thessalonians-3-3", "note": "The Lord is faithful, who shall stablish you, and keep you from evil"},
            {"type": "xref/parallel", "target": "1-john-5-18-19", "note": "He that is begotten of God keepeth himself, and that wicked one toucheth him not"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Mission in the world combined with preservation from the evil one",
            "*   OT Background: Psalm 91:1-12; 121:7 — The LORD shall preserve thee from all evil",
            "*   NT Parallels: Luke 10:19; Romans 16:20; Ephesians 6:10-18; Revelation 3:10",
            "*   Spirit of Prophecy: Testimonies for the Church, vol. 5, p. 573 — Sent into the world to be light and salt",
        ],
        "notes": [
            "*   **Rejection of Isolationism (*Ouk erōtō hina arēs autous ek tou kosmou*):** Christ never calls His followers to monastic retreat or ascetic isolation. The world is the harvest field where God's truth must shine.",
            "*   **Deliverance from the Evil One (*Ek tou ponērou*, G4190):** The Greek masculine/neuter indicates protection from Satan, the ruler of this world, and all his corrupting snares.",
        ],
    },
    16: {
        "tags": ["theme/sanctification", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-15-19", "note": "Because ye are not of the world, but I have chosen you out of the world, therefore the world hateth you"},
            {"type": "xref/parallel", "target": "john-17-14-kjv", "note": "They are not of the world, even as I am not of the world"},
            {"type": "xref/parallel", "target": "romans-12-2", "note": "And be not conformed to this world: but be ye transformed by the renewing of your mind"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Uncompromising spiritual identity and distinctiveness",
            "*   OT Background: Leviticus 20:26 — Ye shall be holy unto me: for I the LORD am holy, and have severed you",
            "*   NT Parallels: 2 Corinthians 6:14-18; Colossians 3:1-3",
            "*   Spirit of Prophecy: Patriarchs and Prophets, p. 607 — God's people called to be a distinct and holy standard",
        ],
        "notes": [
            "*   **Double Affirmation of Non-Worldliness:** By repeating verbatim the statement from verse 14, Jesus underscores that spiritual distinctiveness is not optional or peripheral; it is the essential precondition for effective witness.",
        ],
    },
    17: {
        "tags": ["theme/sanctification", "theme/law", "theme/faith"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalm-119-142", "note": "Thy righteousness is an everlasting righteousness, and thy law is the truth"},
            {"type": "xref/parallel", "target": "psalm-119-151", "note": "Thou art near, O LORD; and all thy commandments are truth"},
            {"type": "xref/parallel", "target": "john-8-31-32", "note": "If ye continue in my word... ye shall know the truth, and the truth shall make you free"},
            {"type": "xref/parallel", "target": "ephesians-5-26", "note": "That he might sanctify and cleanse it with the washing of water by the word"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Sanctification through the objective Word of truth",
            "*   OT Background: Exodus 19:6; Leviticus 11:44-45; Psalm 19:7-11; 119:9, 142, 151",
            "*   NT Parallels: 2 Thessalonians 2:13; 1 Peter 1:22; 2 Peter 1:3-4",
            "*   Spirit of Prophecy: The Great Controversy, p. 593 — God's Word the only safeguard; DA 677",
        ],
        "notes": [
            "*   **Sanctification Defined (*Hagiason autous*, G37):** *Hagiazo* signifies consecration, purification, and dedicated setting apart for sacred ministry. In biblical theology, sanctification is the work of a lifetime, aligning the human mind and character with divine holiness.",
            "*   **The Instrument of Sanctification (*En tē alētheia*, G225):** Holiness is not achieved by emotional ecstasy or human effort, but by the transforming power of truth received and obeyed through the Holy Spirit.",
            "*   **Thy Word Is Truth (*Ho logos ho sos alētheia estin*, G3056 G225 G1510):** God's self-revelation in Scripture is the ultimate, objective benchmark of reality, righteousness, and truth, against which every human philosophy must be tested.",
        ],
    },
    18: {
        "tags": ["theme/prophecy", "theme/faith", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-20-21", "note": "As my Father hath sent me, even so send I you"},
            {"type": "xref/parallel", "target": "matthew-28-19-20", "note": "Go ye therefore, and teach all nations, baptizing them in the name of the Father, and of the Son, and of the Holy Ghost"},
            {"type": "xref/parallel", "target": "2-corinthians-5-20", "note": "Now then we are ambassadors for Christ, as though God did beseech you by us"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Apostolic commission modeled upon the incarnation of the Son",
            "*   OT Background: Isaiah 6:8 — Here am I; send me",
            "*   NT Parallels: Mark 16:15; Acts 1:8; Romans 10:15",
            "*   Spirit of Prophecy: The Acts of the Apostles, pp. 9-16 — The high purpose of the church",
        ],
        "notes": [
            "*   **The Incarnational Model of Mission (*Kathōs eme apesteilas... kagō apesteila autous*):** Just as the Father sent the Son to live among human beings, heal broken hearts, and manifest self-renouncing love, so Christ sends His church into the world as living embodiments of His grace.",
        ],
    },
    19: {
        "tags": ["theme/sanctuary", "theme/redemption", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "hebrews-2-11", "note": "For both he that sanctifieth and they who are sanctified are all of one"},
            {"type": "xref/parallel", "target": "hebrews-10-10", "note": "By the which will we are sanctified through the offering of the body of Jesus Christ once for all"},
            {"type": "xref/parallel", "target": "hebrews-10-14", "note": "For by one offering he hath perfected for ever them that are sanctified"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Priestly self-consecration and the sacrificial basis of sanctification",
            "*   OT Background: Exodus 29:1-37 — Consecration of the priesthood and altar; Leviticus 1:3-4",
            "*   NT Parallels: 1 Corinthians 1:30; Ephesians 5:25-26; Titus 2:14",
            "*   Spirit of Prophecy: The Desire of Ages, p. 678 — Christ the priest and the sacrifice",
        ],
        "notes": [
            "*   **Self-Sanctification for Others (*Hyper autōn egō hagiazō emauton*):** Christ had no sin from which to be cleansed. His 'sanctifying Himself' denotes His voluntary dedication as the unblemished sacrificial victim upon the altar of the cross, consecrating Himself to death that His followers might be truly set apart to God.",
        ],
    },
    20: {
        "tags": ["theme/prayer", "theme/faith", "theme/prophecy"],
        "xrefs": [
            {"type": "xref/parallel", "target": "acts-2-39", "note": "For the promise is unto you, and to your children, and to all that are afar off"},
            {"type": "xref/parallel", "target": "romans-10-14-17", "note": "So then faith cometh by hearing, and hearing by the word of God"},
            {"type": "xref/parallel", "target": "1-peter-1-23", "note": "Being born again, not of corruptible seed, but of incorruptible, by the word of God"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Everlasting intercession extending to all future generations of believers",
            "*   OT Background: Isaiah 53:10-11 — He shall see his seed, he shall prolong his days",
            "*   NT Parallels: John 10:16; 2 Corinthians 5:19-20; Ephesians 2:13-17",
            "*   Spirit of Prophecy: The Desire of Ages, p. 678 — Reaching down the ages to every humble believer",
        ],
        "notes": [
            "*   **The Church Through All Ages:** In a breathtaking expansion of perspective, Christ gathers every future believer under His intercessory wings. From the twelve in the upper room to the final remnant generation at the close of time, every soul who believes through the apostolic word is encompassed in this prayer.",
        ],
    },
    21: {
        "tags": ["theme/covenant", "theme/faith", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-10-38", "note": "That ye may know, and believe, that the Father is in me, and I in him"},
            {"type": "xref/parallel", "target": "john-14-10-11", "note": "Believest thou not that I am in the Father, and the Father in me?"},
            {"type": "xref/parallel", "target": "romans-12-5", "note": "So we, being many, are one body in Christ, and every one members one of another"},
            {"type": "xref/parallel", "target": "galatians-3-28", "note": "There is neither Jew nor Greek... for ye are all one in Christ Jesus"},
            {"type": "xref/parallel", "target": "ephesians-4-3-6", "note": "Endeavouring to keep the unity of the Spirit in the bond of peace. There is one body, and one Spirit"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The organic unity of believers as the supreme witness to Christ's messiahship",
            "*   OT Background: Psalm 133:1 — Behold, how good and how pleasant it is for brethren to dwell together in unity!",
            "*   NT Parallels: 1 Corinthians 12:12-27; Philippians 1:27; Colossians 3:12-15",
            "*   Spirit of Prophecy: Testimonies for the Church, vol. 9, pp. 179-189 — Christian unity the strongest credential",
        ],
        "notes": [
            "*   **Organic Spiritual Unity (*Hina pantes hen ōsin*, G3956 G1520):** Christ prays for a deep, living union among His followers rooted in shared divine life, truth, and agape love. This is the antithesis of worldly sectarian rivalry.",
            "*   **The Supreme Apologetic (*Hina ho kosmos pisteuē*, G2443 G2889 G4100):** Unselfish unity among diverse believers constitutes the most convincing proof to an unbelieving world that Jesus was truly sent by the Father.",
        ],
    },
    22: {
        "tags": ["theme/christ", "theme/sanctification", "theme/covenant"],
        "xrefs": [
            {"type": "xref/parallel", "target": "2-corinthians-3-18", "note": "Changed into the same image from glory to glory, even as by the Spirit of the Lord"},
            {"type": "xref/parallel", "target": "colossians-1-27", "note": "Christ in you, the hope of glory"},
            {"type": "xref/parallel", "target": "1-john-3-2", "note": "When he shall appear, we shall be like him; for we shall see him as he is"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Divine glory bestowed upon the church for holy unity",
            "*   OT Background: Exodus 34:29-35 — Moses' face shining with reflected divine glory",
            "*   NT Parallels: Ephesians 1:17-18; 1 Peter 4:14",
            "*   Spirit of Prophecy: The Desire of Ages, p. 678 — The glory of Christ is His character",
        ],
        "notes": [
            "*   **The Imparted Glory (*Ten doxan... dedōka autois*, G1391 G1325):** The glory of Christ is not outward pomp, but His character of unselfish love and divine holiness. By imparting His Spirit to dwell in believers, He reproduces His loving character within them, binding them together in unbreakable union.",
        ],
    },
    23: {
        "tags": ["theme/covenant", "theme/christ", "theme/grace"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-14-23", "note": "If a man love me, he will keep my words: and my Father will love him, and we will come unto him"},
            {"type": "xref/parallel", "target": "ephesians-3-17-19", "note": "That Christ may dwell in your hearts by faith; that ye, being rooted and grounded in love"},
            {"type": "xref/parallel", "target": "colossians-3-14", "note": "And above all these things put on charity, which is the bond of perfectness"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Perfection in oneness and the staggering measure of the Father's love",
            "*   OT Background: Zephaniah 3:17 — The LORD thy God in the midst of thee is mighty... he will rejoice over thee with joy",
            "*   NT Parallels: Romans 8:38-39; 1 John 4:12-16",
            "*   Spirit of Prophecy: Steps to Christ, pp. 9-15 — God's love for man; DA 679",
        ],
        "notes": [
            "*   **Perfected into One (*Teteleiōmenoi eis hen*, G5048 G1519 G1520):** Believers achieve ultimate spiritual maturity as they dwell in reciprocal love with God and one another.",
            "*   **Loved with the Same Love (*Ēgapēsas autous kathōs eme ēgapēsas*, G25 G846 G2531 G1691):** One of the most breathtaking assurances in Scripture: the Father loves redeemed human beings with the very same tender, everlasting love wherewith He loves His only begotten Son.",
        ],
    },
    24: {
        "tags": ["theme/hope", "theme/second-coming", "theme/christ"],
        "xrefs": [
            {"type": "xref/parallel", "target": "john-14-3", "note": "And if I go and prepare a place for you, I will come again, and receive you unto myself; that where I am, there ye may be also"},
            {"type": "xref/parallel", "target": "1-thessalonians-4-17", "note": "Then we which are alive and remain shall be caught up together with them... so shall we ever be with the Lord"},
            {"type": "xref/parallel", "target": "revelation-21-3", "note": "Behold, the tabernacle of God is with men, and he will dwell with them"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: Eternal communion in the presence of unveiled divine glory",
            "*   OT Background: Isaiah 33:17 — Thine eyes shall see the king in his beauty; Psalm 16:11",
            "*   NT Parallels: 2 Corinthians 5:8; Philippians 1:23; Revelation 22:3-5",
            "*   Spirit of Prophecy: The Great Controversy, pp. 675-678 — The eternal reward of the redeemed",
        ],
        "notes": [
            "*   **The Sovereign Will of the Intercessor (*Thelō*, G2309):** Here Jesus shifts from petition (*erōtō*) to sovereign desire (*thelō* = 'I will'). As the covenant Redeemer, He claims the final fruit of His sacrifice: the eternal companionship of His purchased people.",
            "*   **Beholding Unveiled Glory (*Theōrōsin tēn doxan tēn emēn*, G2334 G1391):** The ultimate beatitude for the redeemed is to behold and partake of Christ's unveiled glory throughout eternal ages.",
            "*   **Pre-Temporal Love (*Pro katabolēs kosmou*, G4253 G2602 G2889):** Confirms the eternal, unoriginated love between Father and Son, antedating all created things.",
        ],
    },
    25: {
        "tags": ["theme/christ", "theme/faith", "theme/judgment"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalm-145-17", "note": "The LORD is righteous in all his ways, and holy in all his works"},
            {"type": "xref/parallel", "target": "matthew-11-27", "note": "No man knoweth the Son, but the Father; neither knoweth any man the Father, save the Son"},
            {"type": "xref/parallel", "target": "john-8-19", "note": "Ye neither know me, nor my Father: if ye had known me, ye should have known my Father also"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The Righteous Father vindicated against a world in darkness",
            "*   OT Background: Genesis 18:25 — Shall not the Judge of all the earth do right?",
            "*   NT Parallels: Romans 3:25-26; Revelation 15:3; 16:5",
            "*   Spirit of Prophecy: The Desire of Ages, p. 679 — Righteousness and mercy harmonized at the cross",
        ],
        "notes": [
            "*   **The Invocation 'Righteous Father' (*Pater Dikaie*, G3962 G1342):** At the climax of the prayer, Christ appeals to God's inherent justice and righteousness (*dikaios*). God's righteousness guarantees that His promises to the Son and the covenant flock will be unfailingly honored.",
        ],
    },
    26: {
        "tags": ["theme/covenant", "theme/christ", "theme/grace"],
        "xrefs": [
            {"type": "xref/parallel", "target": "psalm-22-22", "note": "I will declare thy name unto my brethren"},
            {"type": "xref/parallel", "target": "john-15-9", "note": "As the Father hath loved me, so have I loved you: continue ye in my love"},
            {"type": "xref/parallel", "target": "romans-5-5", "note": "The love of God is shed abroad in our hearts by the Holy Ghost which is given unto us"},
            {"type": "xref/parallel", "target": "ephesians-3-19", "note": "And to know the love of Christ, which passeth knowledge, that ye might be filled with all the fulness of God"},
            {"type": "xref/spirit-prophecy", "target": "des-73-1", "note": "The Desire of Ages, Chapter 73 — 'Let Not Your Heart Be Troubled'"},
        ],
        "correlations": [
            "*   Theme: The ongoing disclosure of the divine Name and the indwelling love of Christ",
            "*   OT Background: Exodus 34:5-7; Psalm 103:1-13 — The tender mercies of the Lord",
            "*   NT Parallels: Galatians 2:20; Colossians 1:27; 1 John 4:16",
            "*   Spirit of Prophecy: The Desire of Ages, pp. 679-680 — The culmination of the High Priestly Prayer",
        ],
        "notes": [
            "*   **Continuous Disclosure (*Egnōrisa kai gnōrisō*, G1107):** Christ declared the Father's character in His earthly walk, and He will continue to declare it through the Holy Spirit and throughout the ceaseless ages of eternity.",
            "*   **Indwelling Agape (*He agapē hēn ēgapēsas me en autois ē*, G26 G1722 G846):** The ultimate purpose of redemption is that the very love wherewith the Father loves the Son shall dwell within the hearts of believers.",
            "*   **Christ in Them (*Kagō en autois*):** The triumphant final words of the prayer: Christ indwelling His people, the everlasting pledge of their victory, peace, and eternal glory.",
        ],
    },
}


def curate_verse(v_num: int) -> bool:
    path = JOHN17_DIR / f"john-17-{v_num}-kjv.md"
    if not path.exists():
        print(f"Error: {path} does not exist")
        return False

    content = path.read_text(encoding="utf-8")
    curation = JOHN17_CURATION.get(v_num)
    if not curation:
        print(f"Warning: No curation data for John 17:{v_num}")
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
        content = content.replace("\n---\n", f"\n{xref_block}---\n", 1)

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


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Curate John 17 entries")
    parser.add_argument("--verse", type=int, choices=range(1, 27), help="Curate a single verse")
    args = parser.parse_args(argv)

    verses = [args.verse] if args.verse else range(1, 27)
    curated_count = sum(1 for v in verses if curate_verse(v))
    print(f"Successfully curated {curated_count}/{len(verses)} verses in John 17")
    return 0


if __name__ == "__main__":
    main()

