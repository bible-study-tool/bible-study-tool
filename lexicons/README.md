# Lexicons

Reference data for original-language study. Files here are **curated reference
data**, not generated artifacts of the pipeline.

## `strongs-list.json` (planned — generated, then committed)

The canonical set of valid Strong's numbers, used by the F2 validator
(`search/validation/strongs.py`) to verify every `strongs-H####` / `strongs-G####`
tag against the authoritative enumeration — catching wrong numbers (the class
of error that once slipped into the deterministic core, G2532 vs G746).

**How it's produced:** extracted from an MIT-licensed Bible-with-Strong's source
(e.g. scrollmapper/bible_databases — its KJV ships with Strong's numbers) via:

```bash
python -m search.validation.build_strongs_list \
  --file <kjv-with-strongs>.json \
  --out lexicons/strongs-list.json
```

**Licensing:** the Strong's *numbers* are a set of public-domain facts; the
extraction carries no verse text, so it stays clean per `NOTICE.md` (KJV is
public domain; scrollmapper is MIT).

Until this file exists, F2 runs in **structural mode** (format + plausible
range only). Once present, F2 upgrades to full canonical verification
automatically. See ROADMAP A4 for the companion goal of a full Strong's
*lexicon* (definitions, transliteration, usage counts).
