# Local performance benchmark

Measured October 18, 2026 against application source `d5b3d7b6cbde94ce752197cf3cfd47e8d9590a24`. The benchmark files and documentation were added afterward; application code was unchanged.

## Workload and scope

Source-linked extractive question answering over 5 bundled runbooks. Local-model generation excluded.

Synthetic local loopback HTTP benchmark. Not production capacity, real users, clinical validation or user growth. These measurements describe one short workload on one machine. They do not establish a capacity ceiling, sustained service-level objective, p99 guarantee, production response time or adoption. No historical speedup is claimed unless a comparison is explicitly defined below.

Environment: Darwin 25.2.0, arm64, 12 logical CPUs, Python 3.12.14. Gunicorn 23.0.0, 1 gthread worker, 8 threads.

- 8 concurrent HTTP clients, 40 untimed warmup requests.
- 3 rounds of 800 measured requests: **2,400 total**.
- Requests use persistent local loopback HTTP connections. The client and server share one machine.
- Every response is checked for HTTP success and workload-specific correctness; failures abort without producing a successful report.
- All data is synthetic and isolated in a temporary directory.

## Results

| Round | Requests | Median latency | p95 latency | Requests/second | Failures |
|---|---:|---:|---:|---:|---:|
| 1 | 800 | 5.685 ms | 39.174 ms | 531.24 | 0 |
| 2 | 800 | 6.216 ms | 43.486 ms | 496.75 | 0 |
| 3 | 800 | 6.349 ms | 45.064 ms | 493.08 | 0 |

Combined latency: **6.074 ms median**, **42.940 ms p95**. Median round throughput: **496.75 requests/second**. All **2,400 requests passed** their checks. p95 is the nearest-rank 95th percentile; throughput includes client scheduling and validation.

## Incremental-indexing comparison

The same `sync` implementation processes **1,000 synthetic Markdown documents / 9,000 passages**. A fresh SQLite database is the full-rebuild baseline; an already indexed, unchanged corpus uses digest-based incremental processing. Each of **7 paired trials** uses the same corpus for both paths, alternating their execution order. Filesystem caching can affect both. A separate run in each trial changes 10 documents (1%).

| Operation | Median time |
|---|---:|
| Full rebuild | 752.459 ms |
| Unchanged incremental sync | 39.438 ms |
| 1% of documents changed | 58.415 ms |

Unchanged incremental sync took **94.76% less time** (**19.08x** the full-rebuild speed). Formula: `100 * (1 - median(incremental) / median(full))`. This measures an existing feature against full rebuilding, not a claimed optimization of a previous product release. A changed-corpus full-rebuild pair was not timed, so no improvement percentage is claimed for the 1% case.

Separately, **300 FTS5 queries** over that corpus returned 10 results each: **0.714 ms median**, **0.897 ms p95**. These are retrieval-function times; they exclude HTTP handling and language-model generation. The HTTP workload above uses the 5 bundled runbooks, not this larger generated corpus.

## Reproduce

```sh
python3.12 -m venv .benchmark-venv
.benchmark-venv/bin/python -m pip install -r benchmarks/requirements.txt
.benchmark-venv/bin/python benchmarks/benchmark.py docsearch --output /tmp/docsearch-benchmark.json
```

Health Passport can select a Java executable with `--java /path/to/java`. Other benchmark modes need no Java. The script creates temporary data, starts only a loopback server and stops it after the run. Compare results only under controlled, comparable machine and workload conditions.

[Recorded JSON](results-2026-10-18.json) contains the source revision, environment, per-round results and comparison timings where applicable.
