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

1. **What problem does this project solve, and what is its unit of work?** Explain answer engineering runbook questions with evidence, identify on-call engineers as the audience, and trace one concrete example through the files above. Use the demonstration output rather than hypothetical impact.
2. **Why did you choose the first design decision?** Retain the existing incremental SQLite FTS5 engine and source line ranges. Show the corresponding implementation and a test that would fail if that property were removed.
3. **How do you protect correctness when inputs or execution change?** Separate extractive answers from actual local-language-model generation so the interface never disguises one as the other. Explain the relevant invalid-input or edge-case test and distinguish a checked property from an untested assumption.
4. **How do you make results inspectable and reproducible?** Return retrieved passages and abstain on empty retrieval; generated answers remain reviewable against their context. Point to actual outputs and recorded commands. Explain why a successful example is weaker evidence than a tested boundary or independently reconciled total.
5. **What would you improve before real deployment or real-data use?** Small synthetic Markdown corpus; lexical retrieval is not semantic search. The small model can hallucinate, answer incorrectly, or follow malicious document instructions. Local demo documents are trusted; no secrets or tools are available to the model. Source citations identify retrieved context, not automatic claim verification. Choose one limitation, describe the missing evidence, and propose a measurable acceptance check rather than promising production readiness.

## Independent exercise

Add a new runbook and a retrieval test that checks the expected source appears in the top three.

Write down the expected behavior before editing. Add a meaningful regression check, run the existing suite, and describe what changed in your own words.

## Contribution and resume guidance

The implementation was developed with substantial AI assistance under Abhijith Viswanathan's direction. The verified contribution is the working artifact and the learning work actually completed, not invented employment or adoption.

Suggested factual bullet after personally validating the demo:

- Implemented and validated answer engineering runbook questions with evidence using SQLite FTS5 · Flask, with incremental retrieval and documented correctness checks and limitations.

Use [VERIFICATION.md](VERIFICATION.md) to add only measured numbers. Do not claim production traffic, users, savings, upstream acceptance or cloud deployment without corresponding evidence.
