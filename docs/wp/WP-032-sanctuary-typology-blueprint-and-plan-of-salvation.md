# WP-032: Sanctuary Typology Blueprint & Chronological Plan of Salvation

status: open
scope: Pillar A (Biblical Corpus & SDA Doctrinal Foundations), Pillar D (Workstation Component) — Interactive spatial and chronological roadmap of the Sanctuary (Fundamental Belief #24).
priority: medium

## Objective

Provide an interactive, typological Sanctuary Blueprint representing the blueprint of the plan of salvation: mapping the earthly shadows (Exodus, Leviticus) to their prophetic timelines (Daniel 8:14) and heavenly realities (Hebrews, Revelation).

## Inputs (read these first)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md`
- Fundamental Belief #24 ("Christ's Ministry in the Heavenly Sanctuary")
- `NOTICE.md` (doctrinal basis)
- `web/` (workstation components)

## Tasks

### Phase 1 — Sanctuary Typological Schema & Knowledge Graph
- [x] Define `data/sanctuary_schema.json` mapping compartments, furniture, services, and spiritual realities:
  - Courtyard: Altar of Burnt Offering (Justification/Cross), Laver (Regeneration/Baptism).
  - Holy Place: Menorah (Spirit/Witness), Shewbread (Word), Altar of Incense (Intercession).
  - Most Holy Place: Ark of the Covenant, Mercy Seat, Law (Judgment/Vindication).

### Phase 2 — Typological Scripture Crosswalk
- [x] Map each station to Old Testament institution, prophetic fulfillment, Hebrews heavenly ministry counterparts, and Revelation throne-room scenes.

### Phase 3 — Interactive Blueprint Workstation Component
- [x] Construct dedicated "Sanctuary" tab using responsive, zero-dependency inline SVG styled with design tokens (`--primary`, `--secondary`, sepia/walnut substrates).
- [x] Interactive furniture hotspots displaying theological significance, daily vs. yearly services, and cross-references.
- [x] Add "Plan of Salvation" chronological slider: Courtyard (AD 31 Sacrifice) $\to$ Holy Place (Inauguration & Heavenly Intercession) $\to$ Most Holy Place (1844 Cleansing of the Sanctuary).

### Phase 4 — Scripture In-Text Breadcrumbs
- [ ] When reading sanctuary passages (e.g. Lev 16, Heb 8–10, Rev 4, 8, 11), display an active Sanctuary Station chip in the inspector.

### Phase 5 — Verification & Validation
- [ ] Verify all scripture anchors in `data/sanctuary_schema.json` resolve validly.
- [ ] Run `scripts/verify_all.sh`.

## Conventions that apply
- ADR-013 (Stewardship and Scalability)
- ADR-025 (Anti-Slop Charter)
- NOTICE.md (Doctrinal Basis)

## Acceptance criteria
- [ ] Interactive Sanctuary blueprint renders cleanly in light sepia and dark walnut substrates.
- [ ] Clicking any station displays theological significance, priestly ministry, and Scripture links.
- [ ] Chronological slider updates visual path from the Cross to the Heavenly Sanctuary.
