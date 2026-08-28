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
| Feeds | `lexicons/strongs-list.json` + `lexicons/strongs-lexicon.json` via `python -m search.validation.build_strongs_lexicon` |

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
| Feeds | cross-validation of the Strong's set; future word-occurrence / usage-count work (A4) |

SHA-256:

```
e4b94058829cf1c67a29b9af1829916984f1554fb9617e49b88c48706ee4a94e  KJV-osis.json
```

### 3. Open Scriptures Hebrew Bible — `OSHB-v.2.2.zip`

| Field | Value |
| --- | --- |
| Upstream | <https://github.com/openscriptures/morphhb> |
| Pinned tag | `v.2.2` (`6a5db284c715`) |
| License | Per upstream: WLC Hebrew text = **public domain**; lemma + morphology annotations = **CC BY 4.0** (attribution required: "Open Scriptures Hebrew Bible Project"). Upstream also warns to avoid NFC normalization of the text — relevant for future A9 corpus work. |
| Feeds | future original-language corpus work (ROADMAP A9); not yet consumed by code |

SHA-256:

```
02f8711a4bd6ee322e7009beae158a51a63ca61ec4e90250ae261149c616c399  OSHB-v.2.2.zip
```

## Generated artifacts (for offline drift detection)

The committed artifacts regenerate byte-identically from the pinned sources
(verified). Their checksums are recorded here so drift can be detected without
re-running the generator:

```
f98d6a8c3b0efbbb5657f59c4039e54abdf2917526201e357422468f91f58443  ../lexicons/strongs-list.json
8af872882f7ea4a2f80c9390d325e3f4840bb63f59edd1b4be7f3b572040ff7b  ../lexicons/strongs-lexicon.json
```

## How to reproduce

```bash
# 1. Fetch the pinned sources into data/ (skips files that already match)
scripts/fetch_sources.sh

# 2. Verify checksums only (offline)
scripts/fetch_sources.sh --check

# 3. Regenerate the committed lexicons
python -m search.validation.build_strongs_lexicon \
  --hebrew data/strongs/hebrew.go --greek data/strongs/greek.go --out-dir lexicons
```

## Policy

* Raw sources stay **out of git** (large, third-party). Only generated,
  license-clean artifacts are committed (see `lexicons/README.md`).
* If an upstream source changes, re-verify its checksum + license, update this
  record (new pin + new SHA-256), regenerate, and review the diff of the
  committed `lexicons/*.json` through the normal MR workflow.
* Nothing in `data/` may be redistributed by the project itself; it is fetched
  locally on demand (see `NOTICE.md` content-sourcing policy).
