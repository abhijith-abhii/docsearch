# Engineering and interview notes

## Why this project

Source-linked search demonstrates information retrieval, indexing, incremental updates, and an auditable user experience. It adds technical substance beyond another CRUD application and remains useful without paid services.

## Decisions

**SQLite FTS5.** Use a mature inverted index and BM25 implementation rather than a hand-written search engine. This makes setup small and the behavior inspectable. The application contributes scanning, filtering, passage boundaries, lineage, incremental synchronization, query construction, and safe HTML rendering.

**Passage retrieval.** Short passages give focused excerpts and line references. Splitting at headings generally preserves topic boundaries; a 60-line cap bounds large sections. The compromise is that related terms across passage boundaries may not match.

**Weighted headings.** Heading matches receive weight 4 versus 1 for body text. This is an explicit heuristic, not a learned model or validated relevance improvement. A future evaluation would use a labeled query set to compare ranking quality.

**Literal AND queries.** The parser extracts words and quotes each for FTS. This avoids accidental query operators, but excludes advanced Boolean and phrase search. SQL itself is parameterized.

**Content hashes and transactions.** Unchanged documents keep their passages. Changed documents replace passages; removed or excluded files are deleted. All synchronization writes share one transaction, so a storage failure preserves the previous index. Reads use a read-only SQLite connection.

**Offline HTML.** The report can be opened without a server. All inserted text is escaped, including source attributes. Exports still contain local source paths and excerpts, so they require review before public sharing.

## Walkthrough

Run `python demo.py` and open the results. Explain the four source passages and their line ranges. Change one example file and rerun the index. Demonstrate that `unchanged` and `updated` counts reflect hashes, then delete a disposable example in a copy and verify its results disappear.

## Challenges worth discussing

- Preventing stale passages from remaining after a document changes or disappears.
- Preserving the previous index on a failed synchronization.
- Keeping user queries from becoming FTS operators or SQL syntax.
- Separating a retrieval score from a calibrated confidence estimate: BM25 scores are for ordering, not probabilities.
- Choosing passage boundaries and documenting when queries can miss a relevant document.

## Contribution record

The initial implementation, verification, examples, and documentation were created with Codex in this task. User review, independent changes, and design ownership have not yet been verified. Present it as a new AI-assisted personal portfolio project. Do not claim to have implemented BM25 itself, built a language model, or demonstrated production-scale search.

Accurate now: “This project builds an incremental documentation index around SQLite FTS5 and returns ranked passages with source line ranges.” Add your specific review and changes once you have performed them.
