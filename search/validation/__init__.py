"""Data-integrity validation for the Bible Study Tool.

The deterministic core is the source of truth, and its reliability depends on
every entry being structurally sound and conforming to the documented schema
(``kc-schema.md``), the tag taxonomy (``tags/taxonomy.json``), and the
contribution standards. This package provides automated validators that catch
exactly the class of errors that silently corrupt the knowledge base.

Validators (each maps to a roadmap item under pillar F):
  F1  schema.py        -- entry frontmatter vs kc-schema + taxonomy
  F2  strongs.py       -- Strong's number verification against a canonical list
  F3  xrefs.py         -- cross-reference targets resolve to real entries
  F4  audit.py         -- broken-link / dead-reference audit

These are designed to be run both as a CLI and (later) from CI so that every
proposed change is gate-checked before it reaches the deterministic core.
"""
