# Deterministic Core vs. AI Layer Boundary

This document defines the precise boundary between the deterministic core and the AI layer.

## Principle

The deterministic core is the **source of truth**. The AI layer is an **assistant** that suggests, discovers, and summarizes — but never asserts.

## Deterministic Core (Guaranteed, Human-Verified)

These elements are curated by humans and are authoritative:
| Element | Location | Who Curates |
| --- | --- | --- |
| Tag taxonomy | `tags/taxonomy.json` | Human contributors |
| YAML frontmatter metadata | Each entry's frontmatter | Human contributors |
| Cross-references (xref/) | `cross_references` field in entries | Human contributors |
| Semantic links (relation/) | `correlations/semantic-links.json` | Human curators only |
| Strong's number mappings | Entry frontmatter and lexicons | Human curators |
| Passage references | Entry frontmatter | Human contributors |
| Entry IDs and naming conventions | `CONTRIBUTION_STANDARDS.md` | Human contributors |
| Index files | `index/` directory | Auto-generated from deterministic data |
| Translation texts | `materials/` directory | Human contributors |

## AI Layer (Suggested, Requires Human Review)

These elements are generated or suggested by the AI and must be reviewed before promotion:
| Element | Location | Review Required |
| --- | --- | --- |
| Word study insights | Entry body (marked with `<!-- AI-GENERATED -->`) | Yes |
| Cross-language semantic link discoveries | `correlations/ai-discovered-links.json` | Yes |
| Thematic connections across passages | Entry body (marked with `<!-- AI-GENERATED -->`) | Yes |
| Translation comparison analysis | Entry body (marked with `<!-- AI-GENERATED -->`) | Yes |
| Summary generation | Entry body (marked with `<!-- AI-GENERATED -->`) | Yes |
| Tag suggestions for new entries | `ai/suggested-tag` in frontmatter | Yes |
| Cross-reference suggestions | Entry body (marked with `<!-- AI-GENERATED -->`) | Yes |
| Semantic field membership suggestions | `correlations/ai-discovered-links.json` | Yes |

## Promotion Workflow

AI-suggested content follows this path:

1.  **AI generates** → stored in `ai-discovered-links.json` or marked in entry body
    
2.  **Human reviews** → checks accuracy, theological alignment, and relevance
    
3.  **Human promotes** → moves to deterministic location (semantic-links.json, entry body)
    
4.  **Human rejects** → kept in `ai-discovered-links.json` with `review_status: "rejected"`
    
5.  **Human modifies** → edits the AI suggestion, then promotes
    

## Rules

1.  AI-generated content is **always provisional** until a human reviewer approves it
    
2.  The deterministic core is the **source of truth** — AI suggestions are never authoritative
    
3.  AI confidence levels (`ai/confidence-high`, `ai/confidence-medium`, `ai/confidence-low`) must accompany any AI tag
    
4.  `ai/` tagged entries must NOT be used for deterministic search until promoted
    
5.  All AI-generated content must be marked with `<!-- AI-GENERATED -->` and `<!-- END AI-GENERATED -->`
    

## Why This Boundary Matters

1.  **Trust**: Users can trust the deterministic core because it's human-verified
    
2.  **Transparency**: AI contributions are clearly marked and separable
    
3.  **Quality**: Human review prevents AI errors from entering the knowledge base
    
4.  **Accountability**: Every AI suggestion can be traced to its source and reviewer
    
5.  **Offline reliability**: The deterministic core works without AI or internet
