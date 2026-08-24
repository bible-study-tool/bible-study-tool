# Cross-Reference Discovery Prompt (MVP)

Use when you want to find connections between passages.

## Instructions

1.  Analyze the passage for all cross-references to other Bible passages
    
2.  Identify thematic connections (same theme, different context)
    
3.  Find fulfillment references (OT prophecy → NT fulfillment)
    
4.  Identify contrasting passages (different perspective on same topic)
    
5.  Find original language connections (same Hebrew/Greek word in different passages)
    
6.  Check `correlations/semantic-links.json` for cross-language word connections
    
7.  Check `correlations/semantic-links-index.json` for quick lookup
    
8.  Mark all AI-generated content with `<!-- AI-GENERATED -->`
    

## Input Format

```
Passage: Genesis reference
```

## Output Format

Structured list of cross-references with:

*   Type: xref/parallel | xref/fulfillment | xref/theme | xref/contrast | xref/word-study | xref/spirit-prophecy
    
*   Target: Passage reference or entry ID
    
*   Explanation: Why this connection matters
