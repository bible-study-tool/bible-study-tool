# ADR-025: Visual Identity, "Divinity Hall Desk" Mental Anchor, and Anti-Slop Design Charter

* **Status:** Accepted
* **Date:** 2026-09-11
* **Scope:** Pillar D (Workstation UX / Design System), Pillar P (Distribution Experience)
* **Deciders:** Project Maintainer & Strategic Orchestrator
* **Consulted:** [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) (Stewardship & Simplicity), [ADR-018](ADR-018-textual-study-workstation-and-themes.md) (Themes), [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) (GUI-First Architecture), AGENTS.md, ROADMAP.md
* **Informs:** Pillar D (UX), WP-030, WP-031, WP-032, WP-033

---

## Context

Following the adoption of [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) (local web GUI as the primary face), the visual direction and ergonomics must be clearly codified. Modern web software frequently falls into one of two undesirable extremes:

1. **1990s Desktop Bloat:** Dense, visually unguided interfaces with overwhelming technical grids that intimidate everyday students.
2. **Contemporary "AI Slop":** Generic dark-slate SaaS dashboards dominated by neon purple highlights, bouncy spring physics, Bento boxes, low-contrast washed-out text, and frivolous "magic sparkle" animations.

Bible study is serious, sustained contemplation of sacred literature. It requires dignity, warmth, legibility, and ergonomic endurance.

## Decision

We adopt the **"Divinity Hall Desk"** mental anchor, a warm organic substrate palette, ergonomic focus modes, and an explicit Anti-Slop Design Charter.

### 1. The Mental Anchor

> *"A brass desk lamp illuminating a solid oak library table in an old university divinity hall. Open parchment, parallel ancient texts, unhurried morning devotions, deep scholarly precision without coldness."*

### 2. Color Palette & Substrates

* **The Core Accent Palette:**
  * **Deep Scripture Indigo (`--primary`):** Anchor of navigation, headers, and active references.
  * **Muted Sanctuary Gold (`--secondary`):** Accents, active selections, and typological markers.
  * **Quiet Olive Green (`--accent`):** Original-language morphology glosses and theological notes.
* **Substrates:**
  * **Light Mode (Default):** Warm sepia/parchment tones (`#FBF8F1` substrate, `#2C2621` high-contrast ink). Strictly no harsh `#FFFFFF` (eliminates ocular glare).
  * **Dark Mode:** Deep walnut and midnight charcoal (`#1A1816` substrate, `#E8E2D5` warm text). Strictly no pitch `#000000` (eliminates halation and OLED smearing).

### 3. Layout & Ergonomics

* **65/35 Default Split:** Scripture is the primary stage (65%), inspector is the companion (35%).
* **Draggable Divider:** A smooth divider (`col-resize`) allows continuous resizing between 40% and 80% Scripture width; double-clicking snaps back to the 65/35 default.
* **Scripture Focus Mode (`f`):** Collapses the inspector pane, centering Scripture in an optimal reading column (65–75 characters per line).
* **Panel Zoom (`z` / `Shift + F`):** Maximizes whichever panel or tab currently has focus (Scripture, Sanctuary Blueprint, Lexicon, Commentary) into a full-width workstation.
* **Tab Double-Click:** Double-clicking any active tab maximizes it to full width; pressing `Escape` restores the split view.
* **Header Hygiene:** The theme selector is relocated into the Settings modal (⚙), leaving the header focused exclusively on reference navigation and search.

### 4. Typographic & Visual Hierarchy

* **Scripture Typography:** Literary serif typefaces engineered for sustained reading (Charter, Georgia, Literata, Cardo, Gentium Plus).
* **Data Disambiguation:** Distinct color tokens differentiate Scripture text, verse numbers, and Strong's concordance tags.
* **Zebra Shading:** An optional subtle alternating background per verse, disabled by default.
* **Progressive Disclosure:** Dense Hebrew/Greek morphology and translation equivalents are tucked behind collapsible disclosure controls (`▸`/`▾`), preventing cognitive overload.

### 5. The Anti-Slop Charter (10 Prohibited Patterns)

1. **No Cyber-Slate & Neon Clones:** No generic purples, teals, or electric cyans.
2. **No Bento Box Chaos:** No fragmented grids of unequal cards competing for attention.
3. **No Frosted Glassmorphism:** No GPU-heavy `backdrop-filter: blur()`.
4. **No Low-Contrast Washed-Out Gray:** Body text must meet strict WCAG AAA contrast against substrates.
5. **No Floating Island Pill Controls:** Controls remain anchored to natural borders.
6. **No "Magic Sparkle" Icons (`✨`):** Theological facts are deterministic, not mystical AI generations.
7. **No Bouncy Spring Physics:** Transitions are instantaneous or quiet 150ms linear fades.
8. **No Gamified 3D Push Buttons:** Clean, flat, dignified scholarly buttons.
9. **No Monospace Overuse:** Monospace is restricted strictly to technical codes and verse indices.
10. **No Disorienting Infinite Scroll:** Explicit chapter and book boundaries preserve reading orientation.

### 6. The Four Theological Pillars

1. **Pillar A — Sanctuary Plan of Salvation Blueprint:** Fundamental Belief #24 spatial and chronological roadmap (Courtyard $\to$ Holy Place $\to$ Most Holy Place).
2. **Pillar B — Plain-English Original Language Nuances:** Translating Hebrew verbal stems (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek tenses/voices into accessible theological glosses.
3. **Pillar C — Prophetic Key Chaining & Master Prophetic Table:** In-context symbol definitions + a dedicated searchable aggregated prophetic lexicon table.
4. **Pillar D — Progressive Spirit of Prophecy Narrative Navigation:** Single-line reference chips by default $\to$ full chapter reading on demand $\to$ `z` zoom.

## Consequences

### Positive
* Delivers a distinct, dignified visual identity that honors the sacred character of Scripture.
* Reduces cognitive fatigue during prolonged study sessions through warm substrates and literary typography.
* Empowers both casual devotional readers (`f` focus mode) and deep research scholars (65/35 split, `z` panel zoom).
* Eliminates trend-chasing UI patterns that age rapidly.

### Negative / Trade-offs
* Custom serif font loading requires careful offline bundling to maintain zero-network operation.
* Draggable split panes require precise touch and mouse event coordination to prevent drag-flicker across frames.
