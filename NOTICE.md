# NOTICE: Purpose, Doctrinal Basis, and Content-Sourcing Policy

## Purpose

This tool is a deterministic, offline-first knowledge base for in-depth Bible
study, built around Seventh-day Adventist beliefs and materials. It presents
concordance and semantic-context data and provides an optional, on-demand AI
assistant. It is intended to aid honest, careful study of Scripture.

## Doctrinal Basis

This project is **not doctrinally "neutral"** in a value-free sense. It is
deliberately built upon, and held accountable to, **the Bible as the standard
of truth, as understood within the Seventh-day Adventist framework**. We hold
these beliefs to be, as far as we currently know, in full accordance with
Scripture.

At the same time, we hold this conviction with the humility of **progressive
light**: understanding of truth is intended to grow and be refined as further
light is received. Accordingly, the material in this knowledge base is open to
correction, deeper study, and revision — but such revision must always be
grounded in Scripture, not imposed upon it. Curated material that is later
found to be unsupported by Scripture is corrected through the normal review
workflow (see `CONTRIBUTION_STANDARDS.md`).

No license can enforce this standard. It is upheld by the project's curation
process and community review — the deterministic core is human-verified, and
all AI-generated content is marked and gated behind human approval.

## Content-Sourcing Policy

The project's own original analytical data (concordance, semantic links,
cross-references, taxonomies, word studies) is licensed under CC BY 4.0
(`LICENSE.content`). However, some source texts this tool is designed to study
are **not owned by this project** and are **not redistributed here**:

* **Ellen G. White (Spirit of Prophecy) writings** and other SDA-published
  study materials are under active copyright held by the Ellen G. White Estate
  and/or the General Conference of Seventh-day Adventists. These are **not
  bundled** in this repository. The tool instead **links out** — pointing users
  to the official resources (e.g., egwwritings.org, the Adventist Digital
  Library) where they may download the text themselves and add it locally.
  Linking is reference, not distribution.

* **Bible translations**: public-domain translations (e.g., KJV, ASV, WEB) and
  the original Hebrew/Greek may be bundled. Copyrighted translations (e.g.,
  NIV, ESV, NRSV, NLT) are **not stored** here; where study requires them, the
  tool is designed around a **user-supplied-text / on-device** model — the user
  loads the translation locally and processing runs on their machine without
  the text being reproduced or stored in this database.

* **Lexical source data** (`data/`, gitignored, fetched on demand via
  `scripts/fetch_sources.sh`): Strong's Concordance (1890, public domain) via
  gmlewis/bible-codes (**Apache-2.0**); KJV-with-Strong's via
  scrollmapper/bible_databases (MIT, KJV public domain); Open Scriptures
  Hebrew Bible (WLC text public domain, morphology CC BY 4.0). None of these
  raw sources are redistributed; only derived, public-domain-fact artifacts
  (`lexicons/*.json`) are committed. See `data/PROVENANCE.md` for pins,
  checksums, and the full record.

This policy keeps the project a reference and an engine, not a republisher, and
keeps the material it hosts within clearly-clean territory.
