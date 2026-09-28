# DocSearch Atlas — learning guide

## What it does

Answer engineering runbook questions with evidence. The intended user is on-call engineers. Browser controls → validated Flask API → project analysis/workflow → results and export.

## Run and demonstrate

Follow the README installation block, then: Ask about backup retention in extractive mode, inspect the cited source, then download the model and compare local-llm mode. Try an unrelated question and inspect the no-evidence response.

## Important files

- `app.py` — local HTTP interface and request/error handling.
- `core.py` — project-specific logic.
- `tests/` — regression and correctness checks.
- `reports/` — recorded outputs and verification evidence.

## Three engineering decisions

1. Retain the existing incremental SQLite FTS5 engine and source line ranges.
2. Separate extractive answers from actual local-language-model generation so the interface never disguises one as the other.
3. Return retrieved passages and abstain on empty retrieval; generated answers remain reviewable against their context.

## Five interview questions

1. **What is the retrieval unit?** Markdown documents are indexed into passages with headings and line references. SQLite FTS5 ranks matching passages, and the response carries the source evidence.

2. **Is this embedding-based retrieval?** No. The implementation uses lexical FTS5 retrieval. That is small and inspectable, but paraphrases with no overlapping terms may be missed.

3. **How does extractive mode differ from generation?** Extractive mode returns retrieved text directly. The optional pinned local FLAN model generates an answer from context; its output is explicitly labeled and remains subject to hallucination.

4. **What happens with no useful evidence?** The app abstains instead of presenting an unsupported answer as fact. Source references help users check supported answers, but citations alone do not guarantee correctness.

5. **How are document updates handled?** The preserved search engine incrementally detects changed and deleted documents. The standalone demo now checks all five bundled documents and an unchanged second indexing run.

## Independent exercise

Add a new runbook and a retrieval test that checks the expected source appears in the top three.

Write down the expected behavior before editing. Add a meaningful regression check, run the existing suite, and describe what changed in your own words.

## Contribution and resume guidance

The implementation was developed with substantial AI assistance under Abhijith Viswanathan's direction. The verified contribution is the working artifact and the learning work actually completed, not invented employment or adoption.

Suggested factual bullet after personally validating the demo:

- Extended an incremental SQLite FTS5 document assistant with source-linked retrieval and optional local FLAN generation; verified 19 checks and an actual model response.

Use [VERIFICATION.md](VERIFICATION.md) to add only measured numbers. Do not claim production traffic, users, savings, upstream acceptance or cloud deployment without corresponding evidence.
