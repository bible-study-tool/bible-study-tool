# Contribution Standards & Review Workflow

*Guidelines, quality standards, and verification procedures for contributing to the Adventist Bible Study Tool.*

---

## 1. Purpose & Core Principles

The Adventist Bible Study Tool is a deterministic, offline-first knowledge base where every fact is pinned, verified, and reproducible. To ensure theological fidelity, linguistic precision, and engineering excellence across all materials, every contribution must adhere to three non-negotiables:

1. **Deterministic Core Precedes AI**: The deterministic core is the source of truth. AI output is strictly provisional, marked with `<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->` comments, and gated behind human review. AI content must never enter `correlations/semantic-links.json` or curated entries without explicit review status.
2. **One Verifiable Step at a Time**: Implement → verify (`scripts/verify_all.sh`) → subagent review of every substantive step → commit with accurate counts → regroup with the user. Never batch unrelated changes.
3. **Do the Best Without Being Wasteful (ADR-013)**: We reject shortsighted toy solutions that do not scale to the whole Bible (66 books, 31,102 verses) or full commentary corpuses, and we reject bloated enterprise overkill with unnecessary dependencies.

---

## 2. Contribution Tracks

There are two primary ways to contribute:

- **Track 1: Curated Theological & Linguistic Materials** (`materials/`, `correlations/`): Curating chapter entries, biblical word studies, cross-reference networks, and Spirit of Prophecy commentary links.
- **Track 2: Code, UX & Architecture Contributions** (`search/`, `web/`, `scripts/`, `docs/decisions/`): Expanding the query engine, improving workstation ergonomics, hardening integrity validators, and maintaining offline performance.

---

## 3. Material Submission Standards (Track 1)

All curated entries under `materials/` must be UTF-8 Markdown and conform to [`kc-schema.md`](kc-schema.md).

### Required Frontmatter Fields (YAML)

Every curated entry MUST include:

```yaml
---
id: gen-1-1-kjv
type: passage
book: book/genesis
chapter: 1
verse: 1
source: kjv
translation: kjv
language: hebrew
tags:
  - material/passage
  - book/genesis
  - theme/creation
  - strongs-H7225
  - strongs-H1254
  - strongs-H0430
status: review    # draft, review, or final
updated: '2026-09-17'
cross_references:
  - xref: john-1-1-kjv
  - xref: col-1-16-kjv
  - xref: heb-1-2-kjv
  - egw: PP.34.1
---
```

### Naming Conventions

- **Passage Entries**: `{book}-{chapter}-{verse}-{source}.md` (e.g. `gen-1-1-kjv.md`, `john-1-14-kjv.md`).
- **Word Studies**: `{language}-{strongs}-{source}.md` (e.g. `hebrew-H7225-kjv.md`, `greek-G3056-kjv.md`).
- **General Study Materials**: `{category}-{topic}-{source}.md` (e.g. `studyguide-sanctuary-typology-sda.md`).

### Tagging Standards

1. **Taxonomy Alignment**: Use tags strictly from the official taxonomy (`tags/taxonomy.json`).
2. **Category Requirements**: Every entry MUST have at least one `material/` tag and one `book/` or `theme/` tag.
3. **Strong's Number Links**: Original language terms MUST link to their corresponding `strongs-H` (Hebrew) or `strongs-G` (Greek) tags.
4. **Tag Formatting**: Tags are lowercase, hyphenated, and prefixed by namespace (e.g. `theme/grace`, `status/review`).
5. **Provisional AI Tags**: AI-suggested tags do not satisfy tagging requirements until human review verifies them.

### Content & Citation Standards

1. **Original Languages**: Hebrew, Aramaic, and Greek terms must include transliteration, Strong's concordance number, and grammatical stem/tense where applicable.
2. **Citation Integrity**: All biblical citations must specify book, chapter, and verse. Spirit of Prophecy quotations must include the standard book code and paragraph citation token (e.g. `PP 44.1`, `DA 19.1`, `GC 678.1`).
3. **Doctrinal Neutrality & Theological Stance**: Align strictly with the historic Adventist doctrinal framework documented in [`NOTICE.md`](NOTICE.md). When multiple interpretations exist within historic Adventist scholarship, present them with fair and charitable exegesis.
4. **AI Comment Boundaries**: Any AI-assisted drafting or note generation MUST be wrapped in explicit HTML comments:
   ```markdown
   <!-- AI-GENERATED -->
   Thematic observation or draft word study note...
   <!-- END AI-GENERATED -->
   ```

---

## 4. Hand Content vs. Generated Artifacts

The repository enforces a strict distinction between human-curated content and deterministic artifacts:

| Category | Locations | Rules |
| :--- | :--- | :--- |
| **Hand Content** | `materials/**.md`, `lexicons/wordgraph-notes-*.json` | Authored and edited by humans (+ provisional AI drafts). Gated by F1–F4 validators. Errors are resolved by editing the markdown file. |
| **Generated Artifacts** | `lexicons/*.json`, `correlations/agreement-ledger.json`, `correlations/apparatus-*.json`, `lexicons/wordgraph-*.json` | Generated deterministically from pinned sources. **NEVER HAND-EDIT.** If an artifact drifts, regenerate it with the documented command and commit the artifact + updated [`data/PROVENANCE.md`](data/PROVENANCE.md) checksum together. |

### The Agreement Ledger Golden Baseline
`correlations/agreement-ledger.json` records what every historical source says about shared Strong's keys. It acts as a **golden baseline tripwire**: if an upstream source is re-pinned and facts change, the test suite fails by design to prevent silent changes from corrupting the core. Disagreements are findings for human review, never auto-resolved.

---

## 5. Engineering & Code Standards (Track 2)

Contributors submitting code, UI components, or scripts must observe the following architectural rules:

1. **Zero New Dependencies (ADR-013)**: The project core uses Python's standard library, SQLite, and established zero-bloat tools. Do not add external Python packages without an approved Architectural Decision Record (ADR).
2. **Vanilla Web Architecture (ADR-024)**: The Web Workstation frontend (`web/`) is written in vanilla ES6+, native HTML5, and CSS3. We use zero frontend frameworks, zero build bundlers, and zero `node_modules`.
3. **Sidecar-Free Database Reads (ADR-027)**: Database queries on `data/bible.db`, `data/macula.db`, and `data/egw.db` must never spawn lingering SQLite `-wal` or `-shm` sidecar files on disk. Always open connections with read-only pragmas (`PRAGMA query_only = ON;`) or appropriate locking.
4. **Two-Layer Integrity Verification (ADR-025, ADR-027)**: All core databases are audited at both file-level (SHA-256 in `data/PROVENANCE.md`) and content-level (table row counts, schema version, and key fingerprints in `data/INTEGRITY.json`).
5. **Decisions Require ADRs**: Any substantive technical decision that is difficult to reverse, establishes precedent, or shapes system architecture must be documented in an ADR under `docs/decisions/` and indexed in [`docs/decisions/INDEX.md`](docs/decisions/INDEX.md).

---

## 6. Local Verification & Testing Harness

Before submitting any Merge Request, run the full verification harness locally:

### 1. Ground Truth & Session Check
```bash
python scripts/status.py
```
Inspect current branch status, uncommitted files, roadmap progress, and test suite count.

### 2. Fast Work Package Pre-Flight Check (for material curation)
```bash
python scripts/wp_check.py --wp WP-011
```
Deterministically checks frontmatter fields, AI comment tag balance (`<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->`), verse text preservation against canonical sources, and scoped schema validation in milliseconds.

### 3. Full Verification Harness (Pre-Merge Gate)
```bash
bash scripts/verify_all.sh
```
Runs every check that CI enforces:
1. **Pytest Suite**: Complete unit and integration test suite (825+ tests) including regeneration tripwires and PROVENANCE checksum gates.
2. **F1 Schema Validator**: Validates all entry frontmatter against `kc-schema.md` and taxonomy.
3. **F2 Strong's Number Validator**: Verifies formatting, ranges, and lexicon crosswalks.
4. **F3 Cross-Reference Integrity Checker**: Verifies that all biblical and thematic cross-reference targets resolve.
5. **F4 Dead-Reference & Link Consistency Audit**: Checks for dead references, broken links, and missing target entries.
6. **F6 SQLite Content Gate**: Verifies `data/bible.db` and `data/macula.db` against `data/INTEGRITY.json`.
7. **Raw-Source Checksum Verification**: Validates pinned external downloads against `data/PROVENANCE.md`.

---

## 7. Review & Curation Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 1. DRAFT     │ ──> │ 2. REVIEW    │ ──> │ 3. FINAL     │ ──> │ 4. UPDATE    │
│ Initial work │     │ Human review │     │ Approved to  │     │ Revisions    │
│ status: draft│     │ status:review│     │ status: final│     │ if required  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Stage 1: Draft
- Contributor creates or scaffolds entry with `status: draft`.
- AI assistant assists with initial drafting, wrapping interpretive notes in `<!-- AI-GENERATED -->` blocks.

### Stage 2: Review
- Entry moves to `status: review` and `updated: YYYY-MM-DD`.
- Reviewer audits entry using the Quality Checklist below.

### Stage 3: Final
- Entry promoted to `status: final` upon human approval.
- Material indexed and committed to Git.

### Stage 4: Update
- If new scholarship, corrections, or better cross-references emerge, entry is marked `status: needs-update` and cycles back through review.

---

## 8. Quality Checklist

Reviewers and contributors must verify the following before approving an entry:

### For Biblical Passage Entries
- [ ] Text verbatim matches the stated translation (KJV, ASV, BSB, or YLT).
- [ ] Book, chapter, and verse references are exact and properly formatted.
- [ ] Hebrew / Greek / Aramaic terms include correct transliteration and Strong's concordance numbers.
- [ ] Pauline discourse markers and argument flow badges (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`, `⟨Purpose: ἵνα⟩`) are accurate.
- [ ] Old Testament citation anchors (`⟨OT Anchor: ...⟩`) point to authentic source passages.

### For Word Study Entries
- [ ] Strong's number matches the lexical root in Brown-Driver-Briggs (BDB) or Abbott-Smith.
- [ ] Definition and semantic range represent biblical usage accurately without anachronistic modern definitions.
- [ ] Hebrew verb stems (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek voices/tenses are correctly categorized.
- [ ] Key biblical occurrences and Septuagint (LXX) translation equivalences are verified.

### For AI-Generated or AI-Assisted Content
- [ ] Strictly enclosed within `<!-- AI-GENERATED -->` and `<!-- END AI-GENERATED -->` comments.
- [ ] Frontmatter reflects `status: review` (never auto-promoted to `final`).
- [ ] Human curator has independently verified all claims, citations, and theological assertions against Scripture and the Spirit of Prophecy.
- [ ] Zero unverified AI hallucinations or circular references.

---

## 9. Git Workflow & Merge Requests

### Branching Model
- **`master`**: The stable, production branch. All commits on `master` must pass `bash scripts/verify_all.sh`.
- **`contrib/<topic>`**: Topic branches for contributors (e.g. `contrib/genesis-day-4`, `contrib/sanctuary-hotfix`).
- **`review/<topic>`**: Staging branches for multi-package curation batches undergoing peer review.

### Conventional Commit Messages
Commits must follow the conventional commit format: `type(scope): summary` followed by a concise body stating what changed and why. **Test and entry counts in commit messages must be accurate** (verify before writing).

Supported commit types:
- `curate(scope)`: New or updated biblical passages, word studies, or cross-references.
- `feat(scope)`: New engine features, UI panels, or tools.
- `fix(scope)`: Bug fixes in search, parsers, or UI.
- `docs(scope)`: Documentation, guides, or ADR additions.
- `test(scope)`: New unit, integration, or regression tests.
- `refactor(scope)`: Code refactoring without changing functionality.
- `chore(scope)`: Tooling, dependency pins, or repository maintenance.

*Commit Examples*:
```bash
curate(genesis): complete Day 3 plant typology and Strong's links (WP-003)
feat(sanctuary): add interactive vector blueprint and chronological slider
fix(macula): resolve 2,541-row role_label drift in SQLite compiler
docs(guide): modernize user guide for web GUI workstation and 8 tools
test(query): add 10 faceted query acceptance tests for C4 engine
```

### Merge Requests (GitLab)
1. Fork or create a topic branch from `master`.
2. Ensure your working tree is clean and `bash scripts/verify_all.sh` passes 100% green.
3. Open a Merge Request on GitLab targeting `master`.
4. Provide a clear summary of changes, listing touched files and work package references.
5. All MRs require at least one human review and green CI before merging.
