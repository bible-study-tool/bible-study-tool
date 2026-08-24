# Macula Dataset Integration Reference

## Overview

Macula is an open-licensed dataset of the Hebrew Bible and Greek New Testament with linguistic annotation including syntax trees, glosses, semantic roles, and morphological parsing. It is maintained by the Eep Talstra Centre for Bible and Computer (ETCBC) at Vrije Universiteit Amsterdam.

## Why Integrate Macula?

Rather than building original-language annotation from scratch, we can integrate Macula's datasets as a foundation for our semantic linking system. This accelerates development and ensures linguistic accuracy.

## Available Macula Datasets

### Macula Hebrew

*   Open-licensed, curated dataset of the Hebrew Bible
    
*   Includes: morphological parsing, syntactic structure, semantic roles, glosses
    
*   Access: [https://tools.bible/tools/macula-greek-and-hebrew-linguistic-datasets](https://tools.bible/tools/macula-greek-and-hebrew-linguistic-datasets)
    

### Macula Greek

*   Open-licensed, curated dataset of the Greek New Testament
    
*   Includes: same annotation layers as Hebrew
    
*   Access: Same as above
    

### Text-Fabric

*   Python library for working with ETCBC/Macula data
    
*   Platform-independent research tool
    
*   Can preprocess data and store in any desired format
    
*   GitHub: [https://github.com/annotation/text-fabric](https://github.com/annotation/text-fabric)
    

### SHEBANQ

*   Web-based query interface for the ETCBC database
    
*   Mini Query Language (MQL) for lexical and grammatical queries
    
*   URL: [https://shebanq.ancient-data.org](https://shebanq.ancient-data.org)
    

## Integration Plan

### Phase 1: Reference Integration (MVP)

1.  Download Macula Hebrew and Greek datasets
    
2.  Create a `lexicons/` directory with Strong's number mappings to Macula entries
    
3.  Reference Macula glosses and definitions in our word study entries
    
4.  No code changes — just data references
    

### Phase 2: Automated Lookup (v1)

1.  Use Text-Fabric Python library to query Macula data
    
2.  Build a lookup script that takes a Strong's number and returns Macula annotations
    
3.  Integrate with the AI prompt templates for word studies
    
4.  Store results in `materials/original-languages/`
    

### Phase 3: Semantic Enrichment (v2)

1.  Use Macula's semantic role annotations to enrich `semantic-links.json`
    
2.  Cross-reference Macula's syntactic trees with our semantic field groupings
    
3.  Use Macula's glosses to improve translation equivalence mappings
    
4.  Generate AI-discovered links from Macula's semantic role data
    

## File Structure for Integration

```
materials/original-languages/
  hebrew/
    macula/
      README.md          # Integration notes
      morphology/        # Macula morphological data
      syntax/            # Macula syntactic data
      glosses/           # Macula gloss data
    lexicon/               # Our Strong's-based lexicon entries
  greek/
    macula/
      README.md
      morphology/
      syntax/
      glosses/
    lexicon/
  lexicons/
    strongs-hebrew.json
    strongs-greek.json
```

## Data Integrity Rules

1.  Macula data is read-only — never modify the original datasets
    
2.  Our entries reference Macula data by Strong's number and passage reference
    
3.  All Macula references must include the dataset version and access date
    
4.  Macula annotations are curated data — they follow the same review workflow as our entries
    

## License Considerations

Macula datasets are open-licensed. Check the specific license terms before redistributing. The project should include proper attribution to ETCBC/Vrije Universiteit Amsterdam.
