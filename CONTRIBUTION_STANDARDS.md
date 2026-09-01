# Contribution Standards & Review Workflow

## Purpose

To ensure consistency, quality, and theological alignment across all materials in the knowledge base.

## Material Submission Standards

### Required Fields (YAML Frontmatter)

Every entry MUST include:

*   `id` — Unique identifier following naming convention
    
*   `type` — Material type from taxonomy
    
*   `book` — Biblical book or category
    
*   `source` — Source attribution
    
*   `tags` — At least one theme tag and one category tag
    
*   `status` — draft, review, or final
    
*   `language` — Language of the content
    
*   `translation` — If applicable
    

### Naming Convention

*   Bible passages: `{book}-{chapter}-{verse}-{source}` (e.g., `gen-1-1-kjv`)
    
*   Word studies: `{lang}-{strongs}-{source}` (e.g., `hebrew-H7225-kjv`)
    
*   General materials: `{category}-{name}-{source}` (e.g., `studyguide-sabbath-school-2026-q3`)
    

### Tagging Rules

1.  Use tags from the official taxonomy only
    
2.  Every entry MUST have at least one `material/` tag and one `book/` or `theme/` tag
    
3.  Original language entries MUST link to the corresponding `strongs-H` or `strongs-G` tag
    
4.  Cross-references MUST use the `xref/` type tags
    
5.  Multiple tags are allowed; use space-separated in the index
    
6.  Tags are lowercase and hyphenated
    
7.  AI-generated content MUST use AI tags and `<!-- AI-GENERATED -->` comments
    
8.  AI-suggested tags are provisional and do not satisfy tagging requirements until approved
    

### Content Standards

1.  All content must be in UTF-8 Markdown
    
2.  Hebrew/Greek text must include transliteration and Strong's number
    
3.  AI-generated content must be marked with `<!-- AI-GENERATED -->` and `<!-- END AI-GENERATED -->`
    
4.  Direct quotes must include citation (book, chapter, page where applicable)
    
5.  No theological bias beyond what's documented in the Adventist doctrinal framework
    
6.  When multiple interpretations exist, present them with appropriate nuance
    

## Local Verification & Tooling (run before every Merge Request)

### Work package pre-flight check
For contributors working on specific work packages, run the fast deterministic pre-flight check:
```bash
python scripts/wp_check.py --wp WP-003
```
This checks AI comment boundaries (`<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->`), verifies that verse quotes and Strong's definitions match canonical lexicons with zero drift, and runs F1–F4 validators on the scoped files.

### Full verification harness
One command runs every check CI runs, with a remedy printed for each failure:

```bash
bash scripts/verify_all.sh
```

What it runs, and what each gate means for you:

1. **Test suite (pytest)** — includes the data-integrity gates below plus the
   *regeneration tripwires* and the *PROVENANCE checksum gate*. Always invoked
   via `python -m pytest`.
2. **F1-F4 validators** — schema, Strong's numbers, cross-references, and
   dead-reference audit over the whole corpus.
3. **Raw-source checksums** — only when the raw sources are present locally
   (`data/` is gitignored; a fresh clone skips this step automatically, and
   the committed artifacts are still verified by the checksum gate).

### Hand content vs. generated artifacts

The two classes of files have different rules:

* **Hand content** — everything under `materials/` you author or curate. The
  F1-F4 validators give you specific, actionable errors (missing field, tag
  not in taxonomy, malformed cross-reference). Fix the entry; never touch the
  generated artifacts to make an error go away.
* **Generated artifacts** — `lexicons/*.json`,
  `correlations/agreement-ledger.json`, and the generated corpus entries
  (`materials/bible/ot/genesis/gen-1-4..31-kjv.md`). These are **never
  hand-edited**: each has a generator, a byte-identical-regeneration test, and
  a recorded checksum in `data/PROVENANCE.md`. If a test says an artifact
  drifted, regenerate it with the command printed in the failure message and
  commit the artifact together with its updated checksum.

### The agreement-ledger golden baseline

`correlations/agreement-ledger.json` records what every source says about
every shared key, and where sources agree or differ. It is a **golden
baseline**: if a pinned *source* is re-pinned and its facts change, the
ledger tripwire fails CI **by design** — that is the review gate that stops
silent upstream changes from entering the deterministic core. The workflow:
inspect the ledger diff (what changed and why), review the new disagreements,
then regenerate and commit the ledger together with its updated
`data/PROVENANCE.md` checksum. Disagreements themselves are *findings* for
human review — never auto-resolved — and gloss phrasing differences between
sources of different eras are recorded as side-by-side `info` readings, not
failures.

## Review Workflow

### 1. Draft Stage

*   Contributor creates entry with `status: draft`
    
*   Entry is added to the knowledge base
    
*   AI pre-tags and suggests cross-references (optional, AI-assisted)
    

### 2. Review Stage

- [ ] [ ] 

  

*   Entry moves to `status: review`
    
*   Reviewer checks:
    - [ ] [ ] 
    
    All required fields present
    
    - [ ] [ ] 
    
    Tags from official taxonomy
    
    - [ ] [ ] 
    
    Hebrew/Greek text accurate (verified against standard lexicons)
    
    - [ ] [ ] 
    
    Cross-references valid and meaningful
    
    - [ ] [ ] 
    
    No theological errors or unsupported claims
    
    - [ ] [ ] 
    
    AI-generated content clearly marked
    
    - [ ] [ ] 
    
    Citations accurate
    

### 3. Final Stage

*   Entry moves to `status: final`
    
*   Added to the index files
    
*   Cross-references updated in related entries
    
*   Commit to Git with descriptive message
    

### 4. Update Stage (if needed)

*   Entry moves to `status: needs-update`
    
*   Contributor makes revisions
    
*   Returns to review stage
    

## Git Workflow

### Branching

*   `main` — Approved, final entries only
    
*   `contrib/` — Contribution branches (e.g., `contrib/genesis-word-studies`)
    
*   `review/` — Review branch for pending entries
    

### Commit Messages

Format: `type(scope): description`

*   `add(gen-1-1): KJV text with Hebrew word study`
    
*   `tag(gen-1-1): add creation theme and cross-references`
    
*   `review(pat-1-1): approved by reviewer`
    
*   `update(strongs-H7225): add semantic range notes`
    

### Pull Requests

*   All contributions go through a pull request
    
*   At least one reviewer must approve
    
*   AI pre-review can flag issues but human approval is required
    

## Quality Checklist

### For Bible Text Entries

- [ ] [ ] 

Text matches the stated translation

- [ ] [ ] 

Passage reference is accurate

- [ ] [ ] 

Hebrew/Greek text is accurate (if included)

- [ ] [ ] 

Strong's numbers are correct

- [ ] [ ] 

Transliteration is correct

### For Word Study Entries

- [ ] [ ] 

Strong's number matches the word

- [ ] [ ] 

Definition is accurate per standard lexicon

- [ ] [ ] 

Usage count is correct

- [ ] [ ] 

Semantic range is comprehensive

- [ ] [ ] 

Key passages are listed

### For AI-Generated Content

- [ ] [ ] 

Marked with `<!-- AI-GENERATED -->`

- [ ] [ ] 

AI tags present in YAML frontmatter

- [ ] [ ] 

Confidence level indicated

- [ ] [ ] 

Human reviewer has approved

## Deterministic Core vs. AI Layer Boundary

This is a critical design principle. Here is what each layer handles:

### Deterministic Core (Guaranteed)

*   Tag taxonomy and controlled vocabulary
    
*   YAML frontmatter metadata
    
*   Cross-references (predefined, verified)
    
*   Semantic links (curated, human-reviewed)
    
*   Strong's number mappings
    
*   Passage references
    
*   Entry IDs and naming conventions
    
*   Index files
    

### AI Layer (Suggested, Requires Review)

*   Word study insights and observations
    
*   Cross-language semantic link discoveries
    
*   Thematic connections across passages
    
*   Translation comparison analysis
    
*   Summary generation
    
*   Tag suggestions for new entries
    
*   Cross-reference suggestions
    

### Rule

**AI-generated content is always provisional until a human reviewer approves it.** The deterministic core is the source of truth. The AI layer is an assistant, not an authority.
