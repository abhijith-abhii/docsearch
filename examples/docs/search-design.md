# Search architecture

Documentation is divided into passages at Markdown headings and line limits.
Each passage retains its relative path and original line range.

## Ranking

SQLite FTS5 provides an inverted index and BM25 ranking. Heading matches receive
more weight than body matches. All query terms must match within one passage.

## Incremental indexing

Content hashes let the index reuse unchanged documents. Changed files replace
their old passages in one transaction; deleted files leave the search results.
