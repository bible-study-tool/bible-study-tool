#!/usr/bin/env python3  
"""  
Lightweight Semantic Search for Adventist Bible Study Tool.
Uses TF-IDF vectorization (scikit-learn) to enable semantic search  
across knowledge base entries. Works offline with no API calls.
This is the MVP embedding-based search — simple, fast, and self-contained.  
"""
import json  
import os  
import sys  
from pathlib import Path
import numpy as np  
from sklearn.feature_extraction.text import TfidfVectorizer  
from sklearn.metrics.pairwise import cosine_similarity
class BibleSearchEngine:  
"""Semantic search engine for the Adventist Bible Study knowledge base."""

```
def __init__(self, repo_root="."):
    self.repo_root = Path(repo_root)
    self.entries = []
    self.vectorizer = None
    self.tfidf_matrix = None
    self.entry_texts = []
    self.entry_ids = []

def load_entries(self, materials_dir="materials"):
    """Load all Markdown entries from the materials directory."""
    materials_path = self.repo_root / materials_dir
    if not materials_path.exists():
        print(f"Warning: {materials_path} does not exist")
        return

    for md_file in materials_path.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(content)

        tags = frontmatter.get("tags", [])
        passage = frontmatter.get("passage", "")
        strongs = [t for t in tags if t.startswith("strongs-")]

        searchable = " ".join([
            passage or "",
            " ".join(tags),
            " ".join(strongs),
            body[:3000] if body else "",
        ])

        self.entries.append({
            "id": frontmatter.get("id", str(md_file)),
            "path": str(md_file.relative_to(self.repo_root)),
            "tags": tags,
            "passage": passage,
            "strongs": strongs,
            "searchable": searchable,
            "frontmatter": frontmatter,
        })

    print(f"Loaded {len(self.entries)} entries")

def build_index(self):
    """Build TF-IDF index from loaded entries."""
    if not self.entries:
        print("No entries loaded. Call load_entries() first.")
        return

    self.entry_texts = [e["searchable"] for e in self.entries]
    self.entry_ids = [e["id"] for e in self.entries]

    self.vectorizer = TfidfVectorizer(
        stop_words="english",
        sublinear_tf=True,
        ngram_range=(1, 2),
        max_features=5000,
    )
    self.tfidf_matrix = self.vectorizer.fit_transform(self.entry_texts)
    print(f"Index built with {self.tfidf_matrix.shape[1]} features")

def search(self, query, top_k=5, min_score=0.1):
    """Search for entries semantically similar to the query."""
    if self.tfidf_matrix is None:
        print("Index not built. Call build_index() first.")
        return []

    query_vec = self.vectorizer.transform([query])
    scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_indices:
        if scores[idx] >= min_score:
            results.append({
                "id": self.entry_ids[idx],
                "score": float(scores[idx]),
                "entry": self.entries[idx],
            })

    return results

def search_by_strongs(self, strongs_number):
    """Find all entries referencing a specific Strong's number."""
    results = []
    for entry in self.entries:
        if strongs_number in entry["strongs"]:
            results.append({
                "id": entry["id"],
                "score": 1.0,
                "entry": entry,
            })
    return results

def search_by_tag(self, tag):
    """Find all entries with a specific tag."""
    results = []
    for entry in self.entries:
        if tag in entry["tags"]:
            results.append({
                "id": entry["id"],
                "score": 1.0,
                "entry": entry,
            })
    return results

def _parse_frontmatter(self, content):
    """Parse YAML frontmatter from Markdown content."""
    frontmatter = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_text = parts[1]
            body = "---".join(parts[2:])
            frontmatter = self._parse_yaml_simple(yaml_text)

    return frontmatter, body

def _parse_yaml_simple(self, yaml_text):
    """Simple YAML parser for flat key-value pairs."""
    result = {}
    current_list_key = None
    current_list = []

    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- ") and current_list_key:
            current_list.append(line[2:].strip())
            continue

        if ":" in line and not line.startswith("-"):
            if current_list_key and current_list:
                result[current_list_key] = current_list
                current_list = []
                current_list_key = None

            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if value:
                result[key] = value
            else:
                current_list_key = key
                current_list = []

    if current_list_key and current_list:
        result[current_list_key] = current_list

    return result
```

def main():  
"""CLI interface for the search engine."""  
import argparse

```
parser = argparse.ArgumentParser(description="Adventist Bible Study Semantic Search")
parser.add_argument("--repo", default=".", help="Path to the knowledge base repo")
parser.add_argument("--query", help="Search query")
parser.add_argument("--strongs", help="Search by Strong's number (e.g., H7225)")
parser.add_argument("--tag", help="Search by tag (e.g., theme/creation)")
parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
parser.add_argument("--build-index", action="store_true", help="Build the search index")

args = parser.parse_args()

engine = BibleSearchEngine(args.repo)

if args.build_index or args.query:
    engine.load_entries()
    engine.build_index()

if args.query:
    results = engine.search(args.query, top_k=args.top_k)
    print(f"\nSearch results for: '{args.query}'\n")
    for i, result in enumerate(results, 1):
        entry = result["entry"]
        print(f"{i}. {entry['id']} (score: {result['score']:.3f})")
        print(f"   Path: {entry['path']}")
        print(f"   Passage: {entry['passage']}")
        print(f"   Tags: {', '.join(entry['tags'][:5])}")
        print()

if args.strongs:
    results = engine.search_by_strongs(args.strongs)
    print(f"\nEntries with Strong's {args.strongs}:\n")
    for i, result in enumerate(results, 1):
        entry = result["entry"]
        print(f"{i}. {entry['id']} — {entry['passage']}")
    print()

if args.tag:
    results = engine.search_by_tag(args.tag)
    print(f"\nEntries with tag '{args.tag}':\n")
    for i, result in enumerate(results, 1):
        entry = result["entry"]
        print(f"{i}. {entry['id']} — {entry['passage']}")
    print()
```

if **name** == "**main**":  
main()
