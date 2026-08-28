# Lexicons

Reference data for original-language study. Files here are **generated from
license-clean sources and committed** — they are derived, public-domain-facts
data (Strong's numbers/definitions), not raw third-party text.

## Files

### `strongs-list.json` — canonical Strong's number set (for F2)
The authoritative enumeration of valid Strong's numbers: **8674 Hebrew (H1-H8674)
+ 5624 Greek (G1-G5624)**. Used by the F2 validator
(`search/validation/strongs.py`) to verify every `strongs-H####` / `strongs-G####`
tag, catching wrong numbers (the class of error that once slipped into the
deterministic core: G2532 vs G746).

### `strongs-lexicon.json` — full Strong's dictionary (for A4 study use)
The complete concordance: every number -> original word, transliteration, and
definition (with roots / KJV usage in `desc`). This is the companion to the
number list, ready for word-study entries.

## How they're generated

From `data/strongs/*.go` (the gmlewis/bible-codes concordance, itself
sourced from the public-domain Strong's concordance):

```bash
# Fetch the pinned sources (checksum-verified; see data/PROVENANCE.md)
scripts/fetch_sources.sh

python -m search.validation.build_strongs_lexicon \
  --hebrew data/strongs/hebrew.go \
  --greek  data/strongs/greek.go \
  --out-dir lexicons
```

## Data provenance & licensing

* **Numbers + definitions** are public-domain facts (original Strong's
  concordance). The generated JSON carries no Bible verse text.
* The raw sources in `data/` (`KJV-osis.json`, `OSHB-v.2.2.zip`, `strongs/*.go`)
  are **third-party and gitignored** — they are downloaded locally to run the
  generator, not committed. See `NOTICE.md` for the content-sourcing policy.
* Cross-validation performed: all 13,001 Strong's codes attested in the tagged
  KJV are present in the canonical list (0 missing), confirming completeness.

## Regeneration

To rebuild after updating the sources, run the command above. Commit the
resulting `lexicons/*.json` (compact, license-clean) — do not commit `data/`.
