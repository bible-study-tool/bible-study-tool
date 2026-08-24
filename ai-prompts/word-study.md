# Word Study Prompt (MVP)

Use when you want a deep word study on a Hebrew or Greek word.

## Instructions

1.  Look up the Strong's number in the knowledge base
    
2.  Find all passages where this word appears
    
3.  Describe the semantic range across occurrences
    
4.  Identify cross-language connections (Hebrew → Greek → English) using `correlations/semantic-links.json`
    
5.  Note any semantic fields the word belongs to (from `correlations/semantic-links.json`)
    
6.  Connect to Adventist theological concepts where relevant
    
7.  Mark all AI-generated content with `<!-- AI-GENERATED -->`
    

## Input Format

```
Strong's Number: H#### or G####
Passage: Genesis reference
Translation: KJV/NKJV/ESV/etc.
```

## Output Format

Structured word study with sections for:

*   Transliteration and pronunciation
    
*   Core definition
    
*   Semantic range
    
*   Key passages (top 5-10)
    
*   Cross-language connections
    
*   Adventist theological relevance
    
*   Original language insights lost in translation
