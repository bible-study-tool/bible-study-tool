# Source Data Provenance

This directory (`data/`) holds **third-party raw source data** used to generate
the committed, license-clean artifacts in `lexicons/`. The raw data is
**gitignored** — a fresh clone reproduces it with `scripts/fetch_sources.sh`,
then regenerates the lexicons with the documented build command.

**Integrity model:** every file below is pinned by SHA-256. If a downloaded
file's checksum does not match this record, the source has changed — do NOT
regenerate the lexicons from it until the change is reviewed (the deterministic
core's guarantees depend on stable, auditable inputs).

## Sources

### 1. Strong's Concordance — `strongs/hebrew.go`, `strongs/greek.go`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/gmlewis/bible-codes> |
| Pinned commit | `c9432716b19d039f06a2aebbd1f10b911c6254b0` (master, 2025-08-27) |
| Mechanism | `regenerate.sh` runs upstream `cmd/strongs2go` over scraped HTML of <https://www.kingjamesbibleonline.org/strongs-concordance/> |
| License | Apache-2.0 (upstream repo, verified at pinned commit). The underlying Strong's Concordance (1890) is public domain. |
|  Feeds | `lexicons/strongs-list.json` + `lexicons/strongs-lexicon.json` via `python -m search.validation.build_strongs_lexicon` |

SHA-256:

```
1a638e96475fa55200b26a2a4f4257fe2a0f02ae9669a6c2fce9c5b29148cdde  strongs/hebrew.go
1553f7b74b1aed2b957cf1d607c5d9d30d9863b0605a4ad0d7e6c0bb13a89462  strongs/greek.go
249d829f92a3e65c06df8c61b1aa1876e1fae60a42ad69205d4f4284b2e9e248  strongs/strongs.go
3eb9fd569360b466128d950eac889e4a5aa48c79c7ddef344bd646f0861ded14  regenerate.sh
```

Content fingerprint: **8674 Hebrew + 5624 Greek = 14,298 entries** (the full
canonical Strong's enumeration; F2's bounds depend on these totals). Note: ~1884
Hebrew / ~109 Greek entries appear as `// DUP - SEE ABOVE` comments in the Go
map because their *spelling key* collides with an earlier entry — they are
distinct, valid Strong's numbers and are all kept.

### 2. KJV with Strong's tags (OSIS) — `KJV-osis.json`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/scrollmapper/bible_databases> |
| Pinned commit | `e1b254cef86d0e65b1a5d1a94b8b112d0f296a2c` (master, 2026-07-10) |
| Path | `sources/en/KJV/KJV-osis.json` |
| License | MIT (upstream repo, verified at pinned commit); KJV text is public domain |
|  Feeds | cross-validation of the Strong's set; future word-occurrence / usage-count work (A4) |

SHA-256:

```
e4b94058829cf1c67a29b9af1829916984f1554fb9617e49b88c48706ee4a94e  KJV-osis.json
```

Edition caveat (discovered by the corpus fidelity test, `search/corpus/test_corpus.py`):
this file's Gen 1:2 reads "And the earth was without form **and** void" — no
comma, where the 1769 Cambridge standard KJV reads "without form**, and** void".
KJV edition variants exist (Oxford/Cambridge/printing families); the pinned
scrollmapper reading is authoritative for GENERATED entries, hand-curated
entries keep their own reading. Compare translations against a standard
edition when curating.

### 2b. American Standard Version (1901) — `ASV.json`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/scrollmapper/bible_databases> |
| Pinned commit | `e1b254cef86d0e65b1a5d1a94b8b112d0f296a2c` (master, 2026-07-10) |
| Path | `sources/en/ASV/ASV.json` |
| License | Public Domain (1901) |
| Feeds | `data/bible.db` multi-translation parallel engine (WP-024 Phase 3) |

SHA-256:

```
1589f16be31b2aa2e9374951ac2ba1ce9566bf3704248b2daf034b3ff9b47b40  ASV.json
```

### 2c. Berean Standard Bible (2020) — `BSB.json`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/scrollmapper/bible_databases> |
| Pinned commit | `e1b254cef86d0e65b1a5d1a94b8b112d0f296a2c` (master, 2026-07-10) |
| Path | `sources/en/BSB/BSB.json` |
| License | Public Domain (CC0 dedication by Bible Hub / Berean Bible, 2023) |
| Feeds | `data/bible.db` modern English parallel engine (WP-024 Phase 3) |

SHA-256:

```
24668c9497def405e472fa157a888fa1a4709a13e3d0e03c1dc0bdcd38fa3adf  BSB.json
```

### 2d. Young's Literal Translation (1898) — `YLT.json`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/scrollmapper/bible_databases> |
| Pinned commit | `e1b254cef86d0e65b1a5d1a94b8b112d0f296a2c` (master, 2026-07-10) |
| Path | `sources/en/YLT/YLT.json` |
| License | Public Domain (1898) |
| Feeds | `data/bible.db` literal verbal-aspect engine (WP-024 Phase 3) |

SHA-256:

```
73c9dd9466ee24cdab7872ec956aae2a8ada2d1c92203e40caeba5a14587dcea  YLT.json
```

### 3. Open Scriptures Hebrew Bible — `OSHB-v.2.2.zip`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/openscriptures/morphhb> |
| Pinned tag | `v.2.2` (`6a5db284c715`) |
| License | Per upstream: WLC Hebrew text = **public domain**; lemma + morphology annotations = **CC BY 4.0** (attribution required: "Open Scriptures Hebrew Bible Project"). Upstream also warns to avoid NFC normalization of the text — relevant for future A9 corpus work. |
| Feeds | the deterministic **Hebrew morphology layer** (`lexicons/morphology-genesis1.json` via `search/corpus/build_morphology.py`): per-word lemma with prefix/suffix decomposition (e.g. `b/7225`), ETCBC morphology codes, stable word IDs, WLC text. Extracted per-book XML lives in `data/oshb/` (gitignored; reproduced by `scripts/fetch_sources.sh`). |

SHA-256:

```
02f8711a4bd6ee322e7009beae158a51a63ca61ec4e90250ae261149c616c399  OSHB-v.2.2.zip
```

### 4. STEPBible TBESH/TBESG brief lexicons — `stepbible/TBESH.txt`, `stepbible/TBESG.txt`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/STEPBible/STEPBible-Data> |
| Pinned commit | `efe428a0047bf7b9c3ce2624f60c252c6e435945` (master, 2026-08-21) |
| Pinned blobs | TBESH `a64990a674d13245ae1e9ed426bc69197c2fbad5`, TBESG `efe271a1dbb73fa01f8fa6e0f164c6687757a9ae` |
| License | **CC BY 4.0** — data by www.STEPBible.org based on work at Tyndale House Cambridge. Attribution required: credit **"STEP Bible"** linked to <http://www.STEPBible.org>. Changes to the data must be recorded (ours are listed in each artifact's `changes_recorded`). Per the file header, do not redistribute the raw files — they are fetched on demand. |
| TBESH caveat | STEPBible's own header notes the Brief lexicon is based on *Abridged BDB by Online Bible* and that *"Permission should be gained from Online Bible before these definitions are applied in any project."* Hebrew brief glosses are therefore recorded as **supplementary** (see the artifact's `license_note`); the Strong's definitions in `strongs-lexicon.json` remain the deterministic core. TBESG is clean (Abbott-Smith 1922 is public domain; gaps filled from MiddleLiddel (PD) and Tyndale scholars). |
|  Feeds | `lexicons/tbesh-glosses.json` (8,674 H-codes, 11,633 records) + `lexicons/tbesg-glosses.json` (5,523 G-codes, 5,709 records) via `python -m search.validation.build_stepbible_lexicon` |

SHA-256:

```
464dccadd95fd8620dd05fa0d7a4caba58ec3c4d5db3ebf38e43d046ca25b591  stepbible/TBESH.txt
312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4  stepbible/TBESG.txt
```

### 5. Clear-Bible Macula Hebrew — Lowfat XML (Whole Old Testament: 39 Books, 929 Chapters)

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/Clear-Bible/macula-hebrew> |
| Pinned commit | `47db250bd55d0d8577f2a94fba114ef16c35b23c` (master, 2024-04-18) |
| Path | `WLC/lowfat/` (929 chapters from `01-Gen-001-lowfat.xml` through `39-Mal-003-lowfat.xml`) |
| License | **CC BY 4.0** (Creative Commons Attribution 4.0 International) — Clear-Bible project. Compatible with project CC BY 4.0 content license. |
| Feeds | `data/macula.db` (ADR-014 normalized whole-OT SQLite relational database, 23,206 verses, 102,118 clauses, 678,077 tokens, 8,193 crosswalk entries) via `python -m search.macula.build_db` and `lexicons/macula-genesis.json` (ADR-012 offline gate artifact) via `python -m search.macula.build_crosswalk`. Extracted XML lives in `data/macula-hebrew/` (gitignored; reproduced by `scripts/fetch_sources.sh`). |

SHA-256:

```
523856a1f2953408d847e8d3fcc231f2bd681e540aa91c349cd9c4e128f30f60  macula-hebrew/01-Gen-001-lowfat.xml
25c7113185946010ce3444db66830709b89635cc1ce6fe94a57b98623ef53a58  macula-hebrew/01-Gen-002-lowfat.xml
defb971195c75028e9e978b41cab6d43adae29833c57c118ae083f8159f224e5  macula-hebrew/01-Gen-003-lowfat.xml
c1097d3b4cdda33b798060af9146f35abf7c6a9452364453db7b950ffd6ede30  macula-hebrew/01-Gen-004-lowfat.xml
7d75adb21daad48cbede09f18ce4a5e0fe6b2b9c5f14dab75602237bdd3401d6  macula-hebrew/01-Gen-005-lowfat.xml
3314dfb6c2eb20bad2256bbe2252291620afe891cede5189395d76dbd63c086c  macula-hebrew/01-Gen-006-lowfat.xml
22481e03b3b3909faf246cd0299b26b398b2dbe90b181d950ee5f034ea575159  macula-hebrew/01-Gen-007-lowfat.xml
18b95fe07178c10f6e92496b897cd056306e04b47ccdf88bf2c321a96b80d7e5  macula-hebrew/01-Gen-008-lowfat.xml
be2028a5911c124e99bf3b5a880460c0363fb98dbd4750da1390cc0c4aa9ff83  macula-hebrew/01-Gen-009-lowfat.xml
8b09b806b8bdae59f0eddfd776e289af1d729274c990d94a12ce1102746d963a  macula-hebrew/01-Gen-010-lowfat.xml
92fd6a334ec8493e4003de2c1cbe062bbe62ef72a9c8e0583b1278bb6265eb19  macula-hebrew/01-Gen-011-lowfat.xml
43f903b7a8f3aff964d1874910e58ebe4361113be61a48121676b51c9552f44d  macula-hebrew/01-Gen-012-lowfat.xml
d3d38e8cf6cf8d3e76a37fed5af639c2e82cb2f13f7dbe0e7e67daedc1ee6e56  macula-hebrew/01-Gen-013-lowfat.xml
d46812c63994ef0d3a407155b4f6ba820de578d9907b92cd97125cc36134393d  macula-hebrew/01-Gen-014-lowfat.xml
a6705e7b5cfeea82362ba2b442adcd78877ce8b082af38522383e5a8a8847d5b  macula-hebrew/01-Gen-015-lowfat.xml
08b413f7e6d2421dd785c1060285d4350e34c450dd400117f9cd452051a0074a  macula-hebrew/01-Gen-016-lowfat.xml
4b07a4c1235d387e5d7d789ffda2d89a156e9478e7cbdc68e7f252a27529739c  macula-hebrew/01-Gen-017-lowfat.xml
015385bb2c0e1ed25656b458c8524ccd1df85691ab2289ac9a2ecf746b165903  macula-hebrew/01-Gen-018-lowfat.xml
e87e81919fa4be44788d40da100fcbedc072d8bb7f228eebffd060a420a4f018  macula-hebrew/01-Gen-019-lowfat.xml
8bb182a0e47640f50e14badc603b691ffd10e0ee4d165a876382d021b3019698  macula-hebrew/01-Gen-020-lowfat.xml
2f9c319335b62524f62f6de6b314b8ddff559f3b94842c74dda95e0d36a5e1c7  macula-hebrew/01-Gen-021-lowfat.xml
dce89ecf995d75c2482339584a1885851bc2eca2ffbcc48d50a61755ffa62dc6  macula-hebrew/01-Gen-022-lowfat.xml
dd6cfc9b14e440d1ca3ea30c033ab6c389ebb5eee4ff094e42d194010a205c78  macula-hebrew/01-Gen-023-lowfat.xml
10c2a4590412fafa24a2dbb82d8ec9e603e2e93266e9767d0de206a05d339394  macula-hebrew/01-Gen-024-lowfat.xml
61105fa1b660b5d0cea033c967587626d523e731ee44c327cb16f731deae981a  macula-hebrew/01-Gen-025-lowfat.xml
4c410e5188192029ad4d74dcaa426c8125ca60979c6492f96ec6e82ed26e282d  macula-hebrew/01-Gen-026-lowfat.xml
3055b41d196ea8eef757d66eb79996475cb610a6a178daafaeddb6ebc5519685  macula-hebrew/01-Gen-027-lowfat.xml
2c9be817e20901dea3a2c721247e103049e3e8befcffc2bf7bd3d51fdceb07ff  macula-hebrew/01-Gen-028-lowfat.xml
d6e8bef33ea92ecac931b03b398341f8a6bfe8880f788816533a6bf571cf0e72  macula-hebrew/01-Gen-029-lowfat.xml
bb775c51c36e66f92e6c44df6002d733cb0c2b9dd1fe5d7fdedb33f5e44ba358  macula-hebrew/01-Gen-030-lowfat.xml
3c6e3f171b01242652a65275a1fbd310066e6150b89f025d6ff307f1ea1682f7  macula-hebrew/01-Gen-031-lowfat.xml
8d3cc416d08925ce38c29202e44772746743beba50c8e5d312aa2babb91548a1  macula-hebrew/01-Gen-032-lowfat.xml
a901ab181ad355d2936b5d590da05cb362988d8fcf6c567d95b660e49c80c04f  macula-hebrew/01-Gen-033-lowfat.xml
5fe300dea28ce470c1fb25cb84d187b3997cee46b60e3a8c243e9656710c7305  macula-hebrew/01-Gen-034-lowfat.xml
45288cb616a857363d3e18618b6190624b84bdb74fd2899b81f250f469e50bfe  macula-hebrew/01-Gen-035-lowfat.xml
bd7c4cecc877102c9d9e402e8b40c5ada443f6da688febf32a5abe070669a976  macula-hebrew/01-Gen-036-lowfat.xml
903306b55fec5ce8c948d42c646b9baddd5c33b2f03d97bc2ff3bcaa08d9b793  macula-hebrew/01-Gen-037-lowfat.xml
99b938147f7f654de55ee09a0e8d68aa4a4ab68b4eab5b71ce6554305d3fb006  macula-hebrew/01-Gen-038-lowfat.xml
7ba083d7a53ecc61f5d92a03e4d30672e3bf5cba44b7e551e62fd70ee74ebd81  macula-hebrew/01-Gen-039-lowfat.xml
12d5df7d164ca342cf956a8c35f831b4a416237e5f15623f565098344e5fcf08  macula-hebrew/01-Gen-040-lowfat.xml
4ff9adcbdd1547719d5b6d72a0f43ab418e639cf47e55fc317bd348972a5fa72  macula-hebrew/01-Gen-041-lowfat.xml
ee70a3f05c39bb0b611e76c2ee5bf6256d9e2520bf495185ea1a58b8873d20de  macula-hebrew/01-Gen-042-lowfat.xml
ead7e5a7e0bda001ef4ee8b3d790b9256b54fee57f66c32fcb23b7fafe9aab1f  macula-hebrew/01-Gen-043-lowfat.xml
3cf7869eeea89cfd053fa1ad3ce2066c1d6e6978357dd9175d014c9f23a5ae69  macula-hebrew/01-Gen-044-lowfat.xml
ec3bc5a1fa53bf24fe9e9de90488b0f6a24470ca9a0740f3522233bbc00f3409  macula-hebrew/01-Gen-045-lowfat.xml
fb35b24bfa6d4198f9acda8cf55bd85e5ba57d93246da57a80c373552e3bc85b  macula-hebrew/01-Gen-046-lowfat.xml
5a690f4a2c6648fa1c1aeca932d98624da73b5451be7ace5c61cb6720e860886  macula-hebrew/01-Gen-047-lowfat.xml
8723fe6189556ea3d0ebdfb9ff139827eeac625c83a998699affb42518f14bdf  macula-hebrew/01-Gen-048-lowfat.xml
4254d4cd76c2b3ffe7a5507dd4947ad1ece013b5de25a53cd35fe07f400fa23a  macula-hebrew/01-Gen-049-lowfat.xml
ae35301fc336395f0d05b4fab1249ab48acc787438e3534279a154ab953044f9  macula-hebrew/01-Gen-050-lowfat.xml
```

### 6. Clear-Bible Macula Greek — Lowfat XML (Whole New Testament: 27 Books, 260 Chapters)

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/Clear-Bible/macula-greek> |
| Pinned commit | `8423afe47b9e8f24b7772e808af45c7159a6fe7e` (master, 2024-04-18) |
| Path | `Nestle1904/lowfat/` (27 books from `01-matthew.xml` through `27-revelation.xml`) |
| License | **CC BY 4.0** (Creative Commons Attribution 4.0 International) — Clear-Bible project. Compatible with project CC BY 4.0 content license. |
| Feeds | `data/macula.db` (whole-Bible linguistic SQLite database across all 66 books, 31,149 verses, 128,078 clauses, 815,856 tokens, 13,538 crosswalk entries) via `python -m search.macula.build_db`. Extracted XML lives in `data/macula-greek/` (gitignored; reproduced by `scripts/fetch_sources.sh`). |

SHA-256:

```
7227c49c078edea5e0d4a81770f85bb22627e4070e8701b74220e2527678a82f  macula-greek/01-matthew.xml
6df302c2cba58e19a0670b047d157be6551f9558eb8bd21c6db4c56d48adf6ae  macula-greek/02-mark.xml
03dfe693eebb9dd69f03f7813c53f42275d0c37f057a3b46c326b2b832dca786  macula-greek/03-luke.xml
8d05ead4d8dfbd094c684d798e4deb7cab28848760a7a9f92da20cc8c3c583f8  macula-greek/04-john.xml
ecc17b4c61065273bd910dd3454cb9628e7c6518200e487ae3de47b9af0e3f49  macula-greek/05-acts.xml
8d988a0907b2e473ad40e355faa158b814de1de2e392f6fb6d7cccb69e81a980  macula-greek/06-romans.xml
046086fb343318cb07b4c859ac8fee8af65f5c4c3208283e6f0fc5a4ba93a3f8  macula-greek/07-1corinthians.xml
f99c4229d6b8c9225123666ecb24ac66db9ded991ad67276df2711c0bde2f37d  macula-greek/08-2corinthians.xml
ab348722a09c46c5c6135eb83e6c7db53cdce07ec81a20168f8c04b05704a725  macula-greek/09-galatians.xml
cc4d35ae9f28e99f946df391a3cbb41c0e1a22b0900f0eacb1806c7661b97aa6  macula-greek/10-ephesians.xml
9b701c6e1b0fc75f6611bdedd678722d2f1673af1f50479453cc39cf2a092555  macula-greek/11-philippians.xml
336c4ea6da31c21fa499a9933487799ea6afc46bccd0bd86ad5dbb7966f40fa9  macula-greek/12-colossians.xml
fd2acd9697d93f8dcbdcfb49902294305bf6d0a3f0a0d2314b34281304121b2b  macula-greek/13-1thessalonians.xml
ba059f5e178925ad4b8998c959631870f29c23f455a769e3f4bac75456419b1b  macula-greek/14-2thessalonians.xml
8f27a6f2099ad9204867820c42e79726b7dd8685ec4b6845dac85f86a0b4758a  macula-greek/15-1timothy.xml
cb0c373052f50a8b4bb980dc8b009b13c3d64537fb03a8f2d9a80519aeb603c4  macula-greek/16-2timothy.xml
cb1f43f8a12fc173069aa8acd0dc45e631bba3bc7ed4d0053e49185f50138d4a  macula-greek/17-titus.xml
ec310d091ebb4e16bc4e474514cead4d7e616ab76f5178eba6cf1c301591fed1  macula-greek/18-philemon.xml
5f6756d30db19952f2f5de6c90425427f23198b1a937ded8953a3f1ebb33effe  macula-greek/19-hebrews.xml
68f7375975158e5a8e8133e076d8e0a76f1bcde788626d9663392b21a357e01f  macula-greek/20-james.xml
7f3c0e41b7743cdc008eb99ea5dc12412bd7a56ee0052cb68528f5c3582fd126  macula-greek/21-1peter.xml
7890c67c425c505edc41c1c7237db51fa0520b1a94bbd100b5ba5325ada0c37b  macula-greek/22-2peter.xml
7847c84e2f1b198b731308f624e24a1c7ac3acebe78c5824dcf4f7a3b261896a  macula-greek/23-1john.xml
97173ba79096267e05efb3ede4872aac6ae3c809afdecd3c64401d07961231fb  macula-greek/24-2john.xml
5778992b84539235143f5c4d8646ad2d3b5023c9c869580e1783efc9cd2b5e4d  macula-greek/25-3john.xml
7270fcdd6e3482bc6550ab699c56b85391e4b2d00dc06e59a868999b71b52bbc  macula-greek/26-jude.xml
44371e641abe0296f77e04e2c10b6e71f935d24652327d25cb1762b784e84571  macula-greek/27-revelation.xml
```

## Generated artifacts (for offline drift detection)

The committed artifacts regenerate byte-identically from the pinned sources
(verified). Their checksums are recorded here so drift can be detected without
re-running the generator:

```
f98d6a8c3b0efbbb5657f59c4039e54abdf2917526201e357422468f91f58443  ../lexicons/strongs-list.json
0be7dec4386de2f3a06739e2be69aa91ee158dd615e3ad5f7cb641b8347be686  ../lexicons/strongs-lexicon.json
```

The STEPBible-derived artifacts regenerate byte-identically as well; their
current checksums are:

```
c8688a08e409daa987ecf04e309ad1da4634d535023bba2394a704135e480a09  ../lexicons/tbesh-glosses.json
8a4d97cf6d819915241f77a95fd3b926e0d9cb03eab52b05a1af8989eea9044d  ../lexicons/tbesg-glosses.json
```

The OSHB morphology artifact regenerates byte-identically as well:

```
efd17409d6ab378789b0e332a10894e6e9145d37f14ed3951d9723d45754e4eb  ../lexicons/morphology-genesis1.json
bb914375dcaba57d4379afb0dcba40d4740218915277a13be270927e564a68b0  ../lexicons/morphology-genesis2.json
3b6bbd3dd0b3c1fd9c32378ac2085b599132ee021600aecd716a1fb750fb6d65  ../lexicons/morphology-genesis3.json
5b09763c05840fd84bba6f0fb2dbee71434f0559ba072590115cee770975079b  ../lexicons/morphology-genesis4.json
78a339b7d5f58183e137cd56f08ced5d32392365f7335c21efade224528d39dc  ../lexicons/morphology-genesis5.json
6d04f7b8efeb7ea37d37c2c7533439ee64297423d120abc3baf90f471ce4b271  ../lexicons/morphology-genesis6.json
b029498d6fdd21660bd534ffb8aae3a34fb9abc5c7d6236cb63cdd96048c372c  ../lexicons/morphology-genesis7.json
0bd304e12ba0943763db44910166f2f26e830be14beebee32fcbffa42e828cc5  ../lexicons/morphology-genesis8.json
bf309896ddca625e8fce9c298ca9b0704593cde5f78ee08f28088e6bf75dd723  ../lexicons/morphology-genesis9.json
122c6b7c307bc7da552dc7023241473c76d94e235b407eba141484121ab22edd  ../lexicons/morphology-genesis10.json
4d25fa1d6ad872b918253ee0f48d0950b801f79ea0668fbb469cce47efa19281  ../lexicons/morphology-genesis11.json
dcf382dd347f542ab067de20bc7f15a4a0749afe4e2186d1b0712411d2a13ee5  ../lexicons/morphology-genesis12.json
48b291b8503f98b01270c9610107d8289815df9bd686e501d02748fd1198139d  ../lexicons/morphology-genesis13.json
dc1bb8c63d7be67f5d59beea5dd509e6cf6ac3b32e217e0e0ded11dc0e5f1642  ../lexicons/morphology-genesis14.json
77db96e201041e23ec70180fb2dd101eab7108812a5387f836ec5a358a008a5f  ../lexicons/morphology-genesis15.json
3b62a26e36ffce7272ef9f0f65ecf6a42c66938c498e8f35519bff91950e8e4c  ../lexicons/morphology-genesis16.json
d56476353c970c944ced3401c3c4d218bf464b551ba4272af6c443fea7185562  ../lexicons/morphology-genesis17.json
8ea44f46380129affbda7b8bb1c25f79d7ebc12bd94ba45b6a41fe4c0043d270  ../lexicons/morphology-genesis18.json
deb5d3459cbb7346f040b7da80c9e14f5bc238b0b167de972d298c70db62e18a  ../lexicons/morphology-genesis19.json
5fb3d4b058fb01a96084f742e4727bd9dd94b6ec67a6cb8a3ec12a5913b88c61  ../lexicons/morphology-genesis20.json
8e62c458cd6504a96ea886c7039b6bc86a7701640e80c35ad2c2a09e656cfe79  ../lexicons/morphology-genesis21.json
78689244d9c84231a7442ebc49e59897cce7010fc60d0a24cd92cac3384b486a  ../lexicons/morphology-genesis22.json
3832c5b58c0cbcd645e503759f3b835de92eb0208d5081ff3f683fd6e5aa30e5  ../lexicons/morphology-genesis23.json
3b44026c0829a8ce18d92752d07a55b34bbbb4340013228b2cdb64ebb320bbcc  ../lexicons/morphology-genesis24.json
9dcc12a0aa1179176f218b13c5bba9553cccd823a5e6eb661b7c7033282924eb  ../lexicons/morphology-genesis25.json
c266b1427ce5f18409b57266f03af7f36eeb81332f7f47ece4ce0a5cb86e0c7b  ../lexicons/morphology-genesis26.json
86f007f864f98eada7a7f1cd8f12945cda59de6c4f4343c25ac7dea9ee1db3e1  ../lexicons/morphology-genesis27.json
f3a5b3ff2331e7ab1da30a9f4a06e078be79d06dc4ba57c3708514fddf05fd23  ../lexicons/morphology-genesis28.json
4a017488e00d4297b58844e99cf3070f15f399de9d027afda6957be822e8a277  ../lexicons/morphology-genesis29.json
0c4fdaeee0c57d3cbe70be49647af6b94d14d8baec65997158342fa40420cd20  ../lexicons/morphology-genesis30.json
91b65309b023cda28330c81374799fc4f192e9afc1ab40b562ee41222cc3559d  ../lexicons/morphology-genesis31.json
e76cff696ad1c61c6eacfdbc9679fbdf36fad4ecb1fbbefffab1a2bbe89695eb  ../lexicons/morphology-genesis32.json
bc2f76067614097c3fe8141b5bc5a15d587c3bcb260b70c57f960237b16d0f79  ../lexicons/morphology-genesis33.json
7e2f7424c8d34ce83c9b2a858109fb7f595577ac8c53a2f5cf06d4c354e1dd27  ../lexicons/morphology-genesis34.json
79b32e1ad54e4db9805a74700820aef1384f7efc6ad0853184722fa306b8633e  ../lexicons/morphology-genesis35.json
23694ef7a3742450678eaa35f3c70a560866f1770c7e254881add63f39a450fd  ../lexicons/morphology-genesis36.json
0b240abd3bac0111d7134e2a4aaec651c9a8c36aaa2ba12fb36b09a346adbed3  ../lexicons/morphology-genesis37.json
a120f0d2384c2f2cdf3b43dab27a577722e2e29b2d403c01c27167b68ffe893e  ../lexicons/morphology-genesis38.json
1af8ca09ed5490ffd8b34fbff6e0b69c82049306d753fc9baf2e7e6ba5055325  ../lexicons/morphology-genesis39.json
aeaef679209d90c18c874be8092b78d4db5d9eb965483954907a4700c6c8293c  ../lexicons/morphology-genesis40.json
61c61e649778a691c7bc50f50f0317e9e42d73ca9647daeb0a12cbc6f87e4292  ../lexicons/morphology-genesis41.json
c6ea8792d6c99692400d967c5ff599f64caea0636eafd450a91f4faa7e49afea  ../lexicons/morphology-genesis42.json
a0b254603079da8647b7942efb0c4a0131d0446a1eeb8ed0b3267f3dd24e9d91  ../lexicons/morphology-genesis43.json
0443b44537c3357ce1d986e3f6ec28e2e450d5a3927ff8ba96effb7efeb7344e  ../lexicons/morphology-genesis44.json
931c2763f1e68e8f19e0257985c49a86211a00f5aaf524bbe19d938531c37a1f  ../lexicons/morphology-genesis45.json
8a0975daa6b25d9fc22d4a1c992547876cb850d60b99c09b3083ba915f5d85dd  ../lexicons/morphology-genesis46.json
567ad05c4d45ddbf3a1783f3ee514e754296630a08b6d1e97ef674010d283463  ../lexicons/morphology-genesis47.json
c8b03781548abc8ee744fe3d6adea41ab795eb83d2a2fa6b04e0bd8c31a869ce  ../lexicons/morphology-genesis48.json
3bf38a7d8245c2b5e49049210208d6ae485bbeaa2ac7f5aa0ad52802e2387d9a  ../lexicons/morphology-genesis49.json
41e471a5bd517edc6d2fb4286972333396ca02e7aa8517414dff79ba396141f1  ../lexicons/morphology-genesis50.json
```

The cross-source Agreement Ledger regenerates byte-identically as well
(verse/word facts for Genesis chapters 1-2; lexicon gloss facts full-canonical):

```
025723001a0204c55fc7c03d1b81c55a45f520581c2b615876a927d5bcc01253  ../correlations/agreement-ledger.json
```

The word-level apparatus (kjv-osis <-> oshb) regenerates byte-identically as
well:

```
5ae9100bbb7f80ab1fe8a992bfab3871ec87b6655876267c1b238f4fb789f33b  ../correlations/apparatus-genesis1.json
4f678a8264262f0796a13e0ac49cc040bc3acaaefd7c6b493e66d1a5cab32616  ../correlations/apparatus-genesis2.json
d3c6e6b2bc74a1de5027568b07589e504d9bee815cf80b4342991ccb74ad23de  ../correlations/apparatus-genesis3.json
a884e638033d9040cb5e179f89497c4caa82b4c782fa72ad9b8a94b2924e386e  ../correlations/apparatus-genesis4.json
9d9304bf08d8bbcba98509928a53075e012ee231160ab779e618123db3d6d1b0  ../correlations/apparatus-genesis5.json
27d487952883df16db6f9881e6a2bb024cfb5919f92dbfef4fdfb0524d195dc4  ../correlations/apparatus-genesis6.json
4b2b463efdfd8c47d654dd90b66c3f106c0faa1baf3a047a693b0a3343f08ba6  ../correlations/apparatus-genesis7.json
7ae21294cf11d2ccb81e3fa5aee5b6e5e1443f79d26e85ac83b9df92c4e3c298  ../correlations/apparatus-genesis8.json
bee3f507c78256eead3353eedb0e2436e036dac994e24cf8fb6023d6cfbf5cfe  ../correlations/apparatus-genesis9.json
9692f82329321d9085a69e4613f8f15c0863bd72c4ec37cc776f93a186e7f033  ../correlations/apparatus-genesis10.json
1f6809c4eb0235a9fbbbcbf704d52826ccb828995f5b9fd8894d073fa1a79934  ../correlations/apparatus-genesis11.json
a6325636976b6f6beffea35fe59e6a23e6da68a40626e3ef19959a43aba86df9  ../correlations/apparatus-genesis12.json
dcfbb529d0f4f9bdbca33832db1404ad3fc3a8b650ce3f6a0ee8b99ba7d93030  ../correlations/apparatus-genesis13.json
a05b2515fada260b7da05d22bec8cc8d73fd2cef6121330d918973238b168fc6  ../correlations/apparatus-genesis14.json
c1cd57d42602698b2d4b6a26a6247d139cd39c7fba0fdb9727f75df52fddd3fc  ../correlations/apparatus-genesis15.json
a9469fb547e26a069e700f02e069a2982d33372e15f0c768196febc852a1d723  ../correlations/apparatus-genesis16.json
668bf2358ef031edc11091f29d84767c2eec65b181b93746a5b38154629e845b  ../correlations/apparatus-genesis17.json
92a5abd01fd30fa467658fe31b9cc451c0dec179d6439f3b728dbe4801a7ae58  ../correlations/apparatus-genesis18.json
d96d4f17a4472aa8d305b36d7541d9c2028e4796952ab4fb3a5430e797950fed  ../correlations/apparatus-genesis19.json
0bcd04debc53e4bd27183f6c2bf7096259ee02a3bbd4f83fd8e762e9a918bb21  ../correlations/apparatus-genesis20.json
8e7506958399e91d560e338c37ee0745227e6dc4212fb1c06e87a6bb26b0dcdc  ../correlations/apparatus-genesis21.json
e4cf9c958f58584132611f84ee311ffd85029a72bb8cfc2dcdf3faae85d7cb16  ../correlations/apparatus-genesis22.json
0ab35bc08e541b1ea55fb0bedee0182623e97a3375d0b6020817504c06f49bda  ../correlations/apparatus-genesis23.json
5bc81935cf8e5d988af3e848c08adf95ea3a1887bb7ce845efa19c10378c89fd  ../correlations/apparatus-genesis24.json
d0b6ef1e941dd1ecc28bf01432d96f59fdc8056025a218d74a19628842fe76d5  ../correlations/apparatus-genesis25.json
0d3752687c2b00fe0cef4743b779edbecc1c5a909888cc92474391fc31c79ec9  ../correlations/apparatus-genesis26.json
ab781ca514f4d779cbabf3471a182dd377138d3e45bc36b5aa5c372192186988  ../correlations/apparatus-genesis27.json
bc0a9ed950e587deeb54e2bc4598aae9f348f5293cb112ffce47970aa5d2e72d  ../correlations/apparatus-genesis28.json
b81e9d18c56ae9958bfa024bac54f83e94ff68a9f44fe7c31a14415055bced0a  ../correlations/apparatus-genesis29.json
aa9146f7217743ca1adac15270a6324296dc5914de93e4d04013209dc161ab56  ../correlations/apparatus-genesis30.json
30769c8174d1efb8cf49d036090e71946f33d446d64e274b7e82fd3f70d1546b  ../correlations/apparatus-genesis31.json
8fc40767197a988f62b45d46996b41d70fc83a1bd7749c4e0ee88267516a4fdd  ../correlations/apparatus-genesis32.json
c419362004fcb434b542954c38ba70196f241c13fea196be8f96b10d0804c018  ../correlations/apparatus-genesis33.json
71b8e428f4b21fb3e1f8035ff70c42bcf3a2a148ce8b6f47b6064b57bb11402e  ../correlations/apparatus-genesis34.json
b1cd999accf45948aa25328a35ce967d31488bac9f4ec8a2416223a613ece245  ../correlations/apparatus-genesis35.json
0c592c2b3f1a5350100e3e39d608a319f69a1cbd140662f3f5cde3fb8aa5582f  ../correlations/apparatus-genesis36.json
4e1ae89f73419cac45ee096ea082197a32d8399e5456d7a2776146df33b65f31  ../correlations/apparatus-genesis37.json
3c3ed600e1ff70ae42879e79277b0949b61263be8444a755e64c2550ad797436  ../correlations/apparatus-genesis38.json
2b93472c9aeb1051fd57f2749f74edb1fd4366276d393de69a3355cdf3109094  ../correlations/apparatus-genesis39.json
41014cb7e3b275eee17ef66a96d6de63d082336e5cb2278b87490f438b670183  ../correlations/apparatus-genesis40.json
8d46d6293e6fbb3df9eca7b89f7934ae3b84032cf348ee4638e4f70378eef6d3  ../correlations/apparatus-genesis41.json
39648f546023b80e7194cc39f4927a6db59443d3331f45162dfe3d2dcc25eeef  ../correlations/apparatus-genesis42.json
60c510e3256166c5cac6f60c33e6c657b4b772796c18e5bff17f46c2cf0819b2  ../correlations/apparatus-genesis43.json
6f4c84f94fbe599e0b7471b311ee1347e05725ec5528e015cc1e869911722feb  ../correlations/apparatus-genesis44.json
bdc84a9d1fba8c3d41c01de4be2c2385b2a4a58dde10255fa91f98dc1f9a0316  ../correlations/apparatus-genesis45.json
10558e0c4533d450ef687e2217e8efb9a290765e0805a6c723ebaf04d2d9d3fa  ../correlations/apparatus-genesis46.json
ddf91bfb10097b9cf4c9e06c6224a8479f1c60d45fbd9d1eea25a63135f25b48  ../correlations/apparatus-genesis47.json
7dcef2a14e6d29566d74d978fa494c1c02a2411a55a2a6e98b03d5d474ab3411  ../correlations/apparatus-genesis48.json
2005db7ea9709b5112a745e1bded3eefea6d9e7914ebda2f3fb197bf0ad11a35  ../correlations/apparatus-genesis49.json
30430b875edbba109af0d9aecfd9294733dcc9a384817ed9f901b822c74f0310  ../correlations/apparatus-genesis50.json
```

The WordGraph lexical knowledge graph (ADR-010) regenerates byte-identically
as well (consumes committed artifacts only — no raw sources):

```
080efd7347446dc2d12b7eecb14c1146d57c2e5c794d897ad5babf6b9fa4c06a  ../lexicons/wordgraph-genesis.json
```

The Macula Hebrew linguistic and syntactic artifact (ADR-012) regenerates byte-identically:

```
63ca95993aab448ea1f7f549d849da70040812069aca6bbd5dd4154f6984930f  ../lexicons/macula-genesis.json
```

## Source edition caveats (discovered by the corpus fidelity tests)

1. **Gen 1:2 comma variant** — scrollmapper KJV-osis reads "without form and
   void" (no comma); the 1769 Cambridge standard reads "without form, and
   void". The pinned source stays authoritative for generated entries; the
   hand-curated entry (typed from a different printing) is human content and
   stays untouched (see `search/corpus/test_corpus.py`).
2. **Unpadded Strong's codes** — scrollmapper writes codes without canonical
   zero-padding in places (e.g. `strong:H068` for H68, `strong:H01` for H1;
   9,257 verses across the file; Genesis 1 happens to be fully padded like
   `H0430`). The numeric value is unambiguous, so the parsers normalize to
   the canonical unpadded form (`int()` strips leading zeros, matching
   `lexicons/strongs-list.json` keys). Genesis 2's first occurrences: H068
   (Gen 2:12 "stone") and H01 (Gen 2:24, span "his father"). Truly malformed
   attributes still fail the fail-fast attribute-count check.
3. **Genesis 2 apparatus additions** — the first *additions* (kjv-osis
   tokens absent from OSHB) appear in Genesis 2 (Genesis 1 had zero):
   periphrastic double-tagging (Gen 2:9 H6779 on "made" and "to grow";
   Gen 2:21 H5307 twice in "caused... to fall") and the proper-name reading
   (Gen 2:21 "upon Adam" tagged H121 where OSHB reads H120 "the man").
   Documented in `correlations/apparatus-genesis2.json` (key Gen.2.9 /
   Gen.2.21); these are tagging quirks, not source corruption.

## How to reproduce

```bash
# 1. Fetch the pinned sources into data/ (skips files that already match)
scripts/fetch_sources.sh

# 2. Verify checksums only (offline)
scripts/fetch_sources.sh --check

# 3. Regenerate the committed lexicons
python -m search.validation.build_strongs_lexicon \
  --hebrew data/strongs/hebrew.go --greek data/strongs/greek.go --out-dir lexicons

# 4. Regenerate the STEPBible modern-gloss lexicons
python -m search.validation.build_stepbible_lexicon \
  --tbesh data/stepbible/TBESH.txt --tbesg data/stepbible/TBESG.txt --out-dir lexicons

# 5. Regenerate the corpus entries (pinned GENERATION_DATE in the module
#    keeps output byte-identical; bump it explicitly on re-runs)
python -m search.corpus.build_genesis1 --repo .                 # Genesis 1:4-31
python -m search.corpus.build_genesis1 --repo . --chapter 2 --verses 1-25  # Genesis 2

# 6. Regenerate the OSHB morphology layers from the extracted XML
python -m search.corpus.build_morphology --repo .               # Genesis 1
python -m search.corpus.build_morphology --repo . --chapters 2  # Genesis 2
python -m search.corpus.build_morphology --repo . --chapters 3  # Genesis 3

# 7. Regenerate the cross-source Agreement Ledger (Genesis 1-2 verse facts)
python -c "from search.agreement.compare import write_ledger; write_ledger('.', chapters=(1,2))"

# 8. Regenerate the word-level apparatus
python -c "from search.agreement.apparatus import write_apparatus; write_apparatus('.')"  # Genesis 1
python -c "from search.agreement.apparatus import write_apparatus; write_apparatus('.', out_path='correlations/apparatus-genesis2.json', chapters=(2,))"  # Genesis 2
python -c "from search.agreement.apparatus import write_apparatus; write_apparatus('.', out_path='correlations/apparatus-genesis3.json', chapters=(3,))"  # Genesis 3

# 9. Regenerate the WordGraph lexical knowledge graph (ADR-010)
python -m search.corpus.build_wordgraph --repo .

# 10. Regenerate the Macula Hebrew linguistic and syntactic artifact (ADR-012)
python -m search.macula.build_crosswalk --repo .
```

## Release Data Bundle Provenance (ADR-006, ADR-024, WP-029)

For zero-Python standalone distributions, pre-compiled biblical databases and derived
lexicons are assembled into a sidecar `dist/data/` bundle.

### Bundle Assembly and Layout

Generated via `scripts/build_release_data.sh`:

```
dist/data/
├── bible.db             # Whole-Bible SQLite (31,102 verses: KJV + BSB/ASV/YLT + Strong's + FTS5)
├── macula.db            # Linguistic SQLite (Hebrew OT + Greek NT syntax & discourse trees)
├── SHA256SUMS           # Cryptographic SHA-256 manifest over every file in the bundle
└── lexicons/            # Canonical derived JSON lexicons (57 files)
    ├── strongs-lexicon.json
    ├── strongs-list.json
    ├── tbesh-glosses.json
    ├── tbesg-glosses.json
    └── morphology-genesis*.json
```

### Build & Verification Commands

```bash
# Build sidecar bundle and tar.gz release archive
scripts/build_release_data.sh

# Build sidecar directory only (without creating archive)
scripts/build_release_data.sh --no-archive

# Verify sidecar bundle integrity against SHA256SUMS manifest
scripts/build_release_data.sh --check dist/data
```

### Provenance & Integrity Model

1. **Deterministic Compilation:** Both SQLite databases (`bible.db` and `macula.db`) are compiled
   strictly from the pinned upstream sources and canonical lexicons listed above, then compacted
   using SQLite `VACUUM INTO` and validated with `PRAGMA quick_check`.
2. **Manifest Generation:** `SHA256SUMS` is computed directly inside the bundle folder across
   `bible.db`, `macula.db`, and `lexicons/*.json`.
3. **Runtime Verification:** At application startup or during the first-run setup wizard
   (WP-029 Phase 4), `search.resource.verify_data_bundle()` validates the sidecar directory against
   `SHA256SUMS` to detect any data corruption or tampering.
4. **Copyright Boundary:** `data/egw.db` is strictly excluded from release bundles per ADR-002,
   ADR-023, and ADR-024. Only public-domain and CC0/openly-licensed biblical and linguistic resources
   are distributed in release bundles.

## Policy

* Raw sources stay **out of git** (large, third-party). Only generated,
  license-clean artifacts are committed (see `lexicons/README.md`).
* If an upstream source changes, re-verify its checksum + license, update this
  record (new pin + new SHA-256), regenerate, and review the diff of the
  committed `lexicons/*.json` through the normal MR workflow.
* Nothing in `data/` may be redistributed by the project itself; it is fetched
  locally on demand (see `NOTICE.md` content-sourcing policy).

