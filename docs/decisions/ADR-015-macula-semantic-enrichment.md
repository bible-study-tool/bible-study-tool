# ADR-015: Macula Semantic Role & Translation-Equivalence Enrichment

- **Status:** Accepted
- **Date:** 2026-09-04
- **Author:** Claude (Anthropic) + Antigravity / OpenCode Pair
- **Pillar:** B (Macula / Linguistic Data Integration) — Goal B3 (Semantic Enrichment)
- **Supersedes / Extends:** [ADR-012](ADR-012-macula-hebrew-linguistic-integration.md), [ADR-014](ADR-014-whole-bible-macula-sqlite-architecture.md)

---

## Context

With ADR-012 and ADR-014, we successfully ingested the Clear-Bible Macula Hebrew corpus across all 50 chapters of Genesis and implemented a whole-Bible SQLite architecture (`data/macula.db`, 1,533 verses, 7,007 clauses, 17,029 constituents, 43,063 tokens).

However, until now, semantic linking in the project operated along two disparate tracks:
1. **Curated Links (`correlations/semantic-links.json`)**: Human-curated conceptual relations (e.g., `sl-001` *rēʾšît* ↔ *archē*, `sl-002` *bārāʾ* ↔ *ktizō*) created manually from theological insights.
2. **AI Discovery (`correlations/ai-discovered-links.json`)**: Cross-language candidate proposals generated purely by embedding cosine similarity (via `search/linking/candidates.py`).

Neither track leveraged the rich, empirical linguistic data provided by Macula:
- **Septuagint (LXX) Translation Equivalence**: Token-level empirical alignments showing exactly which Greek lexemes translated Hebrew terms in antiquity.
- **Syntactic Participant Roles**: Grammatical constituent structures identifying the Agent/Subject (`s`), Action/Predicate (`v`/`p`), Patient/Theme (`o`), and Spatiotemporal Context (`pp`/`adv`).
- **SDBH Semantic Domains**: Conceptual categorization from the Semantic Dictionary of Biblical Hebrew.

Roadmap Pillar B, Goal B3 requires:
> "Phase 3: semantic enrichment — use Macula roles/syntax to enrich semantic-links + translation-equivalence"

---

## Decision

We establish an automated, zero-dependency semantic enrichment engine (`search/macula/enrichment.py`) that bridges the Macula linguistic substrate with our semantic linking pipeline:

1. **Empirical Translation-Equivalence Candidate Discovery**:
   - Rather than relying solely on abstract vector space distances, candidate discovery draws upon Macula's empirical Strong's Hebrew ↔ Greek LXX alignments.
   - Generates grounded `relation/translation-equivalence` proposals with attestation counts (e.g. *bārāʾ* H1254 translated by *poieō* G4160 in Genesis 1:1, 1:21, 1:27, and *ktizō* G2936).
   - Enriches candidate metadata with LXX Greek surface forms, frequency counts, and SDBH semantic domains.
   - Proposes candidates into `correlations/ai-discovered-links.json` under the strict governance of `GateKeeper`, preserving human review status across rebuilds per Non-negotiable 1.

2. **Syntactic Frame & Participant Role Extraction**:
   - Extracts clausal semantic frames from Macula's constituent tree:
     - `Agent / Subject`: Entity initiating the action (e.g. אֱלֹהִים in Gen 1:1, 1:3).
     - `Predicate / Action`: Action or state (e.g. בָּרָא, אָמַר).
     - `Patient / Object / Theme`: Target of action (e.g. הַשָּׁמַיִם וְהָאָרֶץ, אוֹר).
     - `Circumstantial / Prepositional / Adverbial`: Context (e.g. בְּרֵאשִׁית).
   - Provides a clean programmatic and CLI query API: `enrich_verse_frame(verse_ref)` and `enrich_strongs_equivalence(strongs_id)`.

3. **Curated Link Attribution & Enrichment**:
   - Enhances curated links (`correlations/semantic-links.json`) with empirical attestation metadata without modifying human theological consensus.
   - Provides an audit helper ensuring curated links align with empirical LXX witness.

4. **Zero External Dependencies & Strict Fallback**:
   - Utilizes `search/macula/lookup.py` and `search/macula/db.py` (preferring `data/macula.db`, falling back to `lexicons/macula-genesis.json`).
   - Pure Python standard library (`json`, `sqlite3`, `pathlib`).

---

## Consequences

### Positive
- **Grounded Theological Connections**: OT-to-NT cross-language links (e.g., Christ as Creator in Col 1:16 / John 1:1-3) are empirically anchored in LXX translation choices and grammatical roles rather than subjective impressions.
- **Explainable Rationale**: Every proposed link carries empirical citation frequencies and grammatical roles explaining *why* the terms relate.
- **Safety**: Non-negotiable 1 is fully respected: AI/heuristic proposals flow exclusively to `correlations/ai-discovered-links.json`, with human curation gating promotion to `semantic-links.json`.

### Neutral / Trade-offs
- LXX alignments currently cover the OT canon available in Macula Hebrew datasets. New Testament Greek to LXX Greek connections rely on shared Greek Strong's / lemmas.
