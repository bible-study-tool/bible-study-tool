# ADR-012: Macula Hebrew Linguistic Integration & Strong's-LXX Crosswalk

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **WordGraph Scope & Syntactic Gap:** ADR-010 established the WordGraph as a
   lemma-centric lexical graph across Genesis. While morphology files provide
   token prefixes and stems, they lack higher-level syntactic relations (clauses,
   phrases, participant roles like Subject, Verb, Object, Prepositional Phrase).
2. **Cross-Language Alignment (Hebrew ↔ Greek LXX):** Theological study in the
   SDA framework relies extensively on the relationship between Hebrew Old
   Testament concepts and New Testament Greek usage, mediated through the
   Septuagint (LXX). Prior to this, cross-language connections were manual.
3. **Macula Hebrew Resource:** Clear-Bible's Macula Hebrew project (CC BY 4.0)
   provides Lowfat XML annotations for the Hebrew Bible (WLC/OSHB base)
   including clause syntax trees, grammatical roles, SDBH semantic domains, and
   direct word-by-word Greek LXX alignments with Greek Strong's numbers.

## Decision

1. **Upstream Pinning:** Pin `Clear-Bible/macula-hebrew` at commit
   `47db250bd55d0d8577f2a94fba114ef16c35b23c`. Raw Lowfat XML files
   (`01-Gen-{ch}-lowfat.xml`) are downloaded into `data/macula-hebrew/`
   (gitignored) and verified via SHA-256 in `data/PROVENANCE.md`.
2. **Zero-Dependency ElementTree Parser:** Build a fast, deterministic parser
   in `search/macula/extract.py` using Python's standard library
   `xml.etree.ElementTree`. The parser extracts token attributes (morph, SDBH
   domain, LXX Greek form and Greek Strong's) and clause syntax trees (clause
   production rules, phrase boundaries, and roles such as `subj`, `v`, `obj`,
   `pp`, `adv`).
3. **Derived Knowledge Artifacts:** Generate `lexicons/macula-genesis.json`
   containing:
   - `strongs_crosswalk`: Hebrew Strong's ↔ Greek LXX Strong's mapping with
     frequencies, Greek lemmas, and SDBH semantic domains.
   - `syntax`: Per-verse clause hierarchy and phrase roles.
   Committed and verified by the offline provenance gate in CI.
4. **Query Engine & CLI:** Provide `scripts/macula_lookup.py` and
   `search/macula/lookup.py` to allow querying by verse reference (syntax trees
   and clause roles) and by Strong's number (LXX Greek equivalents and semantic
   domains).

## Consequences

* Bridges Old Testament Hebrew and New Testament/LXX Greek with deterministic,
  reproducible lexical alignment.
* Equips the WordGraph and study note generation with sentence syntax and clause
  roles without external heavy libraries (no `lxml`, `text-fabric`).
* Strengthens the factual basis of cross-references and semantic link candidates.

Related: ADR-001 (deterministic core), ADR-006 (provenance), ADR-007 (source
agreement), ADR-010 (WordGraph).
