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
ac7942d89cd78bea1889ad2e2c3e3f4e240a72030823fabcf43c0dbc0816d938  strongs/kjv.go
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
```

The WordGraph lexical knowledge graph (ADR-0010) regenerates byte-identically
as well (consumes committed artifacts only — no raw sources):

```
10d54ecc5b78391cff42ec5a7842af85384ef02340c198c5cd0e7983289b57cd  ../lexicons/wordgraph-genesis.json
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

# 9. Regenerate the WordGraph lexical knowledge graph (ADR-0010)
python -m search.corpus.build_wordgraph --repo .
```

## Policy

* Raw sources stay **out of git** (large, third-party). Only generated,
  license-clean artifacts are committed (see `lexicons/README.md`).
* If an upstream source changes, re-verify its checksum + license, update this
  record (new pin + new SHA-256), regenerate, and review the diff of the
  committed `lexicons/*.json` through the normal MR workflow.
* Nothing in `data/` may be redistributed by the project itself; it is fetched
  locally on demand (see `NOTICE.md` content-sourcing policy).
