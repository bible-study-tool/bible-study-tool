# ADR-003: Standard `---` YAML frontmatter as the entry format

**Status:** Accepted · **Date:** 2026-08-27; recorded 2026-09-01

## Context

The MVP entries used a nonstandard `* * *` + `## key` header convention whose
nested lists (cross_references, related, semantic_links) were not valid YAML;
the loader silently mangled them (cross_references parsed as corrupt
strings). `kc-schema.md` always specified standard frontmatter.

## Decision

Standard `---` YAML frontmatter is the canonical entry format (per
`kc-schema.md`). The corpus was converted; the loader's legacy parser remains
only as a fallback. Validation (F1) enforces the schema: required fields,
taxonomy-conforming tags (`material/` + `book/` or `theme/`), bare
status/translation/level values, structured cross_references/related, and
Strong's tags on original-language entries.

## Consequences

* Nested structures parse correctly everywhere (the --xref feature only
  worked after this fix).
* New entries must validate against F1 before merge; malformed frontmatter is
  a CI failure, not a silent corruption.
