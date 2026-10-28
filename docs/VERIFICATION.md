# Verification report — rebuilt workspace

Created 2026-10-15. These checks apply to the new Angular/ASP.NET implementation.

| Check | Observed result |
| --- | --- |
| Python planner/policy/provider-mock tests | 57 passed |
| Angular production build and strict template checks | Passed |
| ASP.NET Core C# source compilation | Passed with .NET 8 Roslyn and .NET/ASP.NET reference assemblies |
| Standard `dotnet build` here | Blocked by environment process-metadata restrictions; direct C# compilation passed |
| API → Python → Npgsql → database | 20 supported demo question variants succeeded across six intents |
| Custom SQL | All-orders query, ROW_NUMBER query, filtered joins and empty result checked |
| Result cap | 400-order query returned 200 rows and `truncated=true` |
| SQL rejection | DELETE, unsafe function, system-table access and multiple statements returned 422 |
| Database error | Unknown column returned a controlled 422 response |
| Query planning | Demo draft returned SQL without requiring a model key |
| Schema introspection | Three approved tables and their real columns retrieved |
| Saved queries | Validated create/list/delete; invalid name and unsafe SQL rejected |
| Persistence | Saved queries and execution history survived an ASP.NET API restart |
| Reconciliation | Revenue result matched an independently calculated seed-data total |
| Angular browser flows | Query, filter, chart, CSV download, saved-query reopening, pagination, blocked-SQL errors, draft preview, history |
| Responsive/browser errors | 390px viewport without horizontal document overflow; no uncaught browser exceptions during the tested flows |
| Visual inspection | Desktop and mobile screens inspected; temporary QA screenshots are excluded from deliverables |
| LLM response handling | Valid, fenced and unsafe outputs covered with mocks; no paid live-provider call |
| Docker Compose/native PostgreSQL 16 | Configured, not executed here; Docker unavailable |
| GitHub Actions | Workflow included, not run on GitHub |

Database integration used **PGlite**, a PostgreSQL WASM build, via its socket server. The C# API used Npgsql to execute SQL, read-only transactions and EXPLAIN plans. This is not a claim of validation against a native PostgreSQL 16 deployment.

The 20 demo questions are paraphrases of six fixed templates, not an LLM benchmark. Their result does not establish general natural-language accuracy. The custom SQL path is separate and accepts supported SELECT queries outside these templates.

Reports: `integration-results.json` and `browser-results.json`. Reproducible app-level tests: `scripts/smoke_test.py` and `scripts/browser_test.cjs`.

Estimated-cost controls and database timeouts are implemented; exhaustive stress tests, cancellation-race tests and adversarial security testing were not performed. No throughput, production adoption, performance improvement or business-impact metric is claimed.
