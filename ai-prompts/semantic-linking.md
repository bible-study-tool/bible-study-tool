# Cross-Language Semantic Linking Prompt (MVP)

Use when you want to discover conceptual connections across Hebrew, Greek, and English.

## Instructions

1.  Identify the Hebrew and/or Greek words related to the topic
    
2.  Look up each word in `correlations/semantic-links.json`
    
3.  For each relationship found, describe the cross-language equivalence
    
4.  Identify any semantic fields (from `correlations/semantic-links.json`) that include these words
    
5.  Note any contrasts or figurative/metaphorical mappings
    
6.  Check `correlations/semantic-links-index.json` for quick lookup by Strong's number
    
7.  Mark all AI-generated content with `<!-- AI-GENERATED -->`
    

## Input Format

```
Topic: [e.g., "righteousness", "sanctuary", "covenant", "rest"]
Strong's Numbers: [H####, G####]
```

## Output Format

Structured comparison across languages, highlighting:

*   Connections between Hebrew and Greek concepts
    
*   Semantic field memberships
    
*   Translation equivalence mappings
    
*   Contrasts and divergences
    
*   Confidence level for each link (high/medium/low)
