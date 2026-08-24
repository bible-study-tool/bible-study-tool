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
