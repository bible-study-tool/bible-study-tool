# ADR-0022: Historical-Grammatical Context Layer

* Status: Proposed
* Date: 2026-09-06
* Deciders: Project Maintainers, Pair Programming Assistant
* Consulted: [ADR-0001](ADR-0001-deterministic-core-vs-ai.md), [ADR-0010](ADR-0010-wordgraph.md), [ADR-0012](ADR-0012-macula-hebrew-linguistic-integration.md), [ADR-0013](ADR-0013-design-principles-stewardship-and-scalability.md), [ADR-0014](ADR-0014-whole-bible-macula-sqlite-architecture.md), [ADR-0020](ADR-0020-persistent-viewport-workstation-and-comprehension-engine.md)
* Informs: Future C-pillar (Search & Semantic Engine), D-pillar (UX)

## Context

The 1986 General Conference Annual Council official document **"Methods of Bible Study"**
(adventist.org/methodsofbiblestudy, BRI) mandates the **historical-grammatical method** as
the church's approved hermeneutical framework. It explicitly requires interpreters to examine:

> *"The literary, historical, and cultural context of a passage... [seeking] to understand what
> the various writers intended to convey and how their original audiences would have understood
> the text within their specific historical and cultural settings."*

This stands in contrast to the historical-critical method (rejected by the 1986 document), which
subordinates Scripture to secular assumptions. The historical-grammatical method uses historical
and geographical data *as illumination*, not as authority above the text.

Currently the workstation covers three of the four layers of the historical-grammatical method:
- ✅ **Grammatical** — Hebrew verbal stems, Greek aspects, morphology (via Macula + WP-024)
- ✅ **Lexical** — BDB/Abbott-Smith Strong's senses (via WordGraph, ADR-0010)
- ✅ **Intertextual** — OT→NT citation anchors, LXX crosswalk (via ADR-0012/0015)
- ❌ **Historical-geographical** — Author's world, cultural practices, ANE background — **absent**

This gap means a user reading, e.g., John 3 (Nicodemus at night) or Genesis 14 (Lot's rescue)
cannot currently see: what "a ruler of the Jews" meant in first-century Palestine, the cultural
shame of a night visit, or the geography of the King's Highway in the time of Abraham. These
gaps are precisely where misinterpretation is most likely (see the Jeremiah 29:11 problem noted
in `docs/HOW_TO_STUDY_THE_BIBLE.md`).

## Proposals Under Evaluation

Three implementation options are under consideration:

### Option A — Curated YAML Front-Matter Annotations (Minimal, Deterministic)

**Mechanism:** Add a `historical_context:` block to the verse markdown YAML frontmatter.
Authors (or AI under review) annotate specific verses with structured fields:

```yaml
historical_context:
  era: "Second Temple period (circa 4 BC – 70 AD)"
  location: "Jerusalem, Judea — under Roman occupation (Procurator Pilate)"
  cultural_note: "Pharisees held significant civil authority; night visits avoided public scrutiny."
  source: "Josephus, Antiquities 18.1.3; cf. DA 167.1"
```

- **Pros:** Fully deterministic, peer-reviewable, zero new dependencies, consistent with ADR-0001
  (AI content marked and gated), works today
- **Cons:** Hand-curation does not scale to 31,102 verses; coverage will be uneven
- **Verdict:** Best for high-value curated chapters (John 1, 17; Romans; Genesis 1–3)

### Option B — Integrated Open Dataset (`data/history.db`)

**Mechanism:** Ingest a pinned, open-licensed ANE/biblical-geography dataset into a new SQLite
database (`data/history.db`) — analogous to how `data/macula.db` ingested Macula. Candidate
sources (all with open or CC licenses):

| Dataset | Content | License |
|---|---|---|
| **OpenBible.info Geography** | Lat/lon + description for ~4,000 biblical places | CC BY |
| **STEPBible TOTHT** (Tyndale OT Historical Text) | Cultural-era tagging per pericope | CC BY-SA 4.0 |
| **Logos Factbook** | Not open — excluded per ADR-0002 |
| **TIPNR** (STEPBible) | Proper Name Registry (people, places, nations) | CC BY 4.0 |
| **Carta / BibleAtlas** | Map data — check license, some open |

A new inspector tab (e.g., Tab `6`, key `H`) would surface:
- **Era panel**: Period, ruling empire, socio-political context (Second Temple, Divided Kingdom, Exile)
- **Location panel**: Geographical context; place name in Hebrew/Greek; latitude/longitude
- **Cultural note**: ANE practices, Jewish customs, Roman law relevant to the verse

- **Pros:** Scalable to the whole Bible; consistent with how we integrated Macula (ADR-0012/14)
- **Cons:** New dependency, new ingestion pipeline, new validator, significant scoping work
- **Verdict:** The right long-term answer; appropriate for a future work package

### Option C — Per-Book Historical Preambles in Corpus (Hybrid)

**Mechanism:** For each curated book, add a book-level `{book}/README.md` with:
- Historical era, authorship context, original audience
- Map reference (external OpenBible.info link for now; future: embedded)
- Key cultural assumptions the reader must know before starting

And link it from the TUI's book-header display (shown when entering a new book in the workstation).

- **Pros:** Ships fast; deterministic; enriches without new infrastructure
- **Cons:** Book-level granularity only; not verse-specific
- **Verdict:** Good complement to Option A; can be done immediately

## Decision (Deferred — Requires Discussion)

**No architectural decision made yet.** This ADR is `Proposed` pending team review.

Recommended sequencing:
1. **Immediate (this session or next):** Implement Option C — per-book historical preambles
   for John and Genesis. Zero risk, high educational value.
2. **Near-term (next work package):** Implement Option A — add `historical_context:` to the
   YAML frontmatter schema (`kc-schema.md`) and seed curated chapters.
3. **Long-term (new pillar or C-series WP):** Evaluate Option B — `data/history.db` using
   STEPBible TIPNR + OpenBible.info geography, following the Macula ingestion pattern
   (ADR-0014). Pin upstream commit + SHA-256, add F5 validator, expose in Tab 6.

## Constraints

- All data sources must be open-licensed and pinnable (ADR-0002, ADR-0006).
- Historical content in verse annotations is subject to AI-content review gates (ADR-0001).
- No "historical-critical" interpretations may enter the knowledge base: historical data
  illuminates the text; it never overrides or subordinates Scripture. This boundary is explicit
  in the 1986 "Methods of Bible Study" and in ADR-0001.
- Scalability to 31,102 verses is non-negotiable (ADR-0013): any Option A annotations
  must be value-justified (high-traffic passages first).

## Consequences (if Accepted)

* The workstation would achieve full historical-grammatical method coverage as defined by the
  official SDA hermeneutical standard.
* A new `historical_context` YAML key would require schema validation (kc-schema.md update,
  F1 validator update).
* Option B would create `data/history.db` (gitignored raw; derived artifacts committed) and
  require a new `scripts/fetch_sources.sh` entry with upstream commit pin + SHA-256.
