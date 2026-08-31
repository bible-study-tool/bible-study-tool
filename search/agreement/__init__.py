"""Source Agreement Layer — cross-source comparison as first-class data.

Every ingested source is compared against every other on shared keys:

  * agreement  = deterministic corroboration, stronger than either source alone
  * disagreement = a reviewable finding encoding tagging philosophy and
    lexicon nuance that no single source has by itself

Architecture (approved plan): a fact registry + agreement ledger, with the
golden-baseline CI gate layered on top. Hard CI gates protect machine-generated
artifacts and source re-pins only; human-content differences become soft
findings for review, never CI walls.

Modules:
  facts.py   -- the fact model + one adapter per pinned source (S1)
  compare.py -- comparison engine + Agreement Ledger generation (S2)

Fact types (phase 1):
  verse_text    key = 'Gen.1.4'            value = verse text
  word_strongs  key = 'Gen.1.4'            value = sorted multiset of the
                verse's Strong's codes (segmentation-neutral: sources split
                words differently, so comparison is per-VERSE multiset;
                per-word detail lives in meta for the later alignment phase)
  lexicon_gloss key = 'H1254'              value = gloss string
"""
