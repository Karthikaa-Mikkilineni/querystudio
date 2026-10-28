# Application maintenance evidence

## Scope

This extends the existing Angular 20.3 / ASP.NET Core 8 application. It does not introduce a new application, athlete/customer data, Azure integration, hosted release, or production operation. The live query tests use Npgsql with **PGlite 0.5.11 / PostgreSQL 18.6 WASM** over its socket server: one underlying database connection, multiplexed clients. This does not validate the configured native PostgreSQL 16 Docker target.

## Changes

- Removed repeated workspace-file reads/deserialization from GET /api/history and GET /api/saved with a process-local snapshot. Existing single-process ownership and semaphore remain. Mutation copies the two lists first; only successful temporary-file replacement publishes the new snapshot. Failed writes leave the readable snapshot unchanged. Record types are immutable. External edits/multiple API owners are unsupported; restart to reread external changes. This trades a bounded resident snapshot for less repeated parsing.
- Made planner HTTP timeout configurable (`PlannerTimeoutSeconds`, default30, clamped0.1–120). Planning and save endpoints now return controlled504 on cancellation/timeout and503 on dependency failure; query endpoint already had these guards.
- Added HTTP integration tests and Playwright regressions to existing checks and CI definition. CI was authored, not run on GitHub here.

## Executed validation

- Existing SQL policy/provider-mock tests:57 passed.
- New HTTP endpoint suite:23 passed. Validation400, policy/column errors422, malformed JSON400, schema200, capped results200, saved-query201/204/404, execution history; fault-injected validator/planner timeouts504 and availability errors503. Fault injection uses a real local HTTP service, not real database timeouts.
- Existing Playwright script:12 named checks spanning query execution, filters/charts, CSV download, saved queries, pagination, rejected SQL, draft preview, history, mobile overflow and uncaught browser errors. These are one scripted scenario, not12 independently isolated tests.
- New Playwright script:five checks. Query editing through live API; saved queries survive browser reload; UI cancellation ignores delayed response; accessible504 error; CSV escaping/formula-neutralization/zero values. The last three use explicit HTTP interception. They do not assert PostgreSQL query cancellation.
- Local release rehearsal: optimized build -> prior baseline build rollback -> optimized redeploy. Both directories serve compiled Angular assets, use the same workspace path and seeded PGlite service. Health, schema, frontend, query smoke, saved ID and history checked after each restart. No database migration was needed or tested.
- Atomic-write failure injection: intentionally blocked the temporary path with a directory; a failed save did not enter the snapshot; removing the blocker allowed save. Saved entry persisted across rollback/redeploy.

## Reproduce

Normal host: install .NET8, Node22, Python3.12; `pip install -r query_service/requirements.txt`; `npm ci --prefix web`; `npm run build --prefix web`; `dotnet publish api -c Release -o <release>`; use Compose on a Docker-capable host. Existing CI includes new HTTP and browser scripts. Configure `ASKDB_BUILD` and `ASKDB_DOTNET` for isolated dependency-fault API process.

Restricted-host execution used:

```
/tmp/apollo-python/bin/python -m pytest query_service/tests -q
npm ci --prefix web
npm run build --prefix web
npm install --prefix devtools
npx --prefix web playwright install chromium
python3 scripts/prepare_benchmark.py
/tmp/apollo-python/bin/python scripts/benchmark_history.py
/tmp/apollo-python/bin/python scripts/run_local_qa.py
```

`compile_restricted.py` uses .NET8 SDK Roslyn/reference assemblies directly because the standard CLI cannot retrieve process metadata on this host. It needs `DOTNET_ROOT` and `NPGSQL_DLL`, defaults matching recorded /tmp setup. C# compilation and application execution passed; standard `dotnet build`, Docker and hosted deployment are not claimed. New local runner starts all services in one network namespace. Install Npgsql8.0.6 from NuGet. Python environment packages are pinned in query_service/requirements.txt; devtools npm lock pins PGlite and socket server.

Raw reports live in `evidence/maintenance/`. Screenshots and local workspace/user history are excluded from archive. Benchmarks use generated state, not real personal data. Existing docs/VERIFICATION.md describes the earlier verification snapshot; this file supersedes it for maintenance changes.
