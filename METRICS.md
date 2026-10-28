# History endpoint performance benchmark

GET /api/history retrieves the history displayed by Angular. Removed repeated whole-file read/JSON parsing through a process-local snapshot; mutations publish only after a successful atomic file replacement.

| Configuration | Measured requests | Median HTTP ms | p95 HTTP ms |
| --- | ---: | ---: | ---: |
| Baseline | 240 | 6.861 | 11.577 |
| Snapshot | 240 | 0.931 | 1.974 |

Median reduction: **86.4%**. All 480 payload hashes identical. Six rounds with baseline/optimized order alternating, 8 warmups and 40 measured requests per configuration per round. Same seeded 837,704-byte JSON: 100 history entries and 100 saved entries with ~4KB SQL, within configured limits. Each history response returns 50 entries. This targets a populated workspace; smaller files may benefit less. Warm sequential HTTP timings include localhost request/serialization/transport; not browser render time, concurrent load, database query speed or production throughput. Warm filesystem cache benefits both configurations. One Linux shared host; no independent-host confidence claim.

.NET8.0.21 runtime / SDK8.0.415 direct Roslyn; Npgsql8.0.6; Python3.12 / httpx0.28.1; Node and hardware details in environment.json. scripts/benchmark_history.py and raw history-benchmark.json retain samples and payload hashes. scripts/prepare_benchmark.py restores saved baseline sources in a temporary build tree.
