# WP-031: Master Prophetic Key Table & Original-Language Theological Nuances

status: open
scope: Pillar B (Original Languages), Pillar C (Prophetic Structure) — Plain-English theological glosses for Hebrew/Greek grammar + aggregated prophetic symbols lexicon and in-context chaining.
priority: high

## Objective

Make the rich linguistic nuances of the original languages immediately accessible without formal seminary training, and provide a comprehensive, searchable Master Prophetic Key Table linking biblical symbols directly to their cross-canonical definitions and Scripture anchors.

## Inputs (read these first)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md`
- `search/corpus/grammar_nuance.py` (existing Python verbal stem & tense nuance engine)
- `data/macula.db` (morphology tags for Hebrew and Greek)
- `search/linking/` (lexicon resolvers)
- `web/` (GUI frontend components)

## Tasks

### Phase 1 — Original-Language Nuance Gloss Engine
- [ ] Expose existing `search/corpus/grammar_nuance.py` engine (`explain_verb()`) via study service / HTTP API endpoints.
- [ ] Verify coverage across all Hebrew stems (Qal, Niphal, Piel, Pual, Hiphil, Hophal, Hitpael) and Greek aspects (Aorist, Present, Perfect, Middle).
- [ ] Render nuance cards in the inspector morphology tab with progressive disclosure.

### Phase 2 — Master Prophetic Lexicon Dataset
- [ ] Compile deterministic dataset `data/prophetic_lexicon.json` mapping biblical symbols to definitions and primary canonical proof texts (Day=Year, Beast=Kingdom, Water=Peoples, Horn=Power/King, Rock=Christ, etc.).
- [ ] Link historical SDA prophetic consensus citations.

### Phase 3 — Aggregated Prophetic Key Table UI
- [ ] Build full-width workstation tab ("Prophetic Lexicon") with a searchable, filterable table.
- [ ] Support category filters (Time, Entities, Elements) and prophetic book scopes (Daniel, Revelation, Zechariah).

### Phase 4 — In-Context Prophetic Symbol Chaining
- [ ] In Scripture reading view, subtly badge canonical prophetic symbols.
- [ ] Clicking a symbol opens an in-context definition card with immediate links to defining passages.

### Phase 5 — Verification & Validation
- [ ] Add unit tests verifying all proof scriptures in `data/prophetic_lexicon.json` resolve in `BibleDB`.
- [ ] Run `scripts/verify_all.sh`.

## Conventions that apply
- ADR-013 (Stewardship and Scalability)
- ADR-019 (Human-Accessible Original Languages)
- ADR-025 (Anti-Slop Charter)

## Acceptance criteria
- [ ] Verbs in Gen 1:1, John 1:1, and Rom 3:24 display plain-English nuance cards.
- [ ] Prophetic Lexicon table filters symbols and meanings in real time.
- [ ] In-context symbols in Daniel 7 and Revelation 12 link directly to defining scriptures.
