# QueryStudio — Full-Stack SQL Analytics Workspace

**ASP.NET Core 8 / C# · Angular / TypeScript · PostgreSQL · Python / FastAPI**

QueryStudio is the Angular/.NET implementation of the AskDB analytics workspace. The interface retains the AskDB name. It supports custom SQL, live schema exploration, reusable saved queries, persistent execution history, charts, result filtering, sorting, pagination and CSV export. A separate Python service provides SQL policy checks and optional natural-language query drafting.

## Start the app

Install Docker Desktop with Compose, then from this directory run:

```sh
docker compose up --build
```

Open **http://localhost:8080**. No API key is needed for SQL mode or the explicitly labeled demo templates. The synthetic database has 40 customers, 400 orders, and 1,200 line items.

### Try the workflow

1. Run the regional revenue query that opens in the editor.
2. Filter the results or switch to Chart; export the result as CSV.
3. Name the query and save it. Open **Saved queries** and load it again.
4. Select **Preview table** in the schema explorer to inspect data.
5. Write a new SELECT, use joins/aggregation or supported window functions, and run it with Ctrl/Cmd+Enter.
6. Open **Query history** to reuse a previous execution; saved queries and history survive API restarts.
7. Try `DELETE FROM analytics.orders` to see a rejected statement. Nothing is deleted.
8. In **Ask in plain language**, select an example and load its SQL draft. Review, then run it.

The no-key question mode is six deterministic example intents, not an unrestricted model. Custom SQL is independent of those templates. No demo-mode LLM accuracy is claimed.

To stop: `docker compose down`. To reset: `docker compose down -v` **deletes the local database, saved queries and history**.

## Architecture and design

| Component | Implementation |
| --- | --- |
| Angular frontend | Standalone component, typed HttpClient service, signals, forms, responsive layout, SQL editing, tables/charts and workspace views |
| ASP.NET Core API | Minimal endpoints, dependency injection, typed planner client, query service, Npgsql repository, rate limiting, validation and cancellation |
| PostgreSQL analytics store | Relational constraints, indexes, synthetic seed data, restricted SELECT role and explicit read-only transactions |
| Python planner | SQLGlot AST validation, deterministic examples, optional OpenAI-compatible provider |
| Local workspace metadata | Bounded JSON saved-query/history store, SemaphoreSlim coordination, temporary-file-and-rename writes, separate persistent volume |

The workspace store is deliberately separate from the read-only analytics connection. Query history keeps normalized SQL, timestamp, mode, status, row count and elapsed time, not result rows or question text. **SQL literals may contain sensitive values**: keep this local and use synthetic data. It is a single-user, single-API-process workspace, not a multi-user SaaS product.

### Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | API liveness |
| `GET /api/schema` | Approved schema, data types, examples and configured planner mode |
| `POST /api/plan` | Draft SQL from `{ "text": "Revenue by region" }`; does not execute |
| `POST /api/query` | Execute `{ "sql": "SELECT ..." }` or a supported `{ "text": "..." }` question |
| `GET /api/saved` | List saved queries |
| `POST /api/saved` | Validate and save `{ "name": "...", "sql": "..." }` |
| `DELETE /api/saved/{id}` | Delete a saved query |
| `GET /api/history` | Latest 50 execution records |
| `DELETE /api/history` | Clear local execution history |

Python endpoints are internal and not exposed by Compose. ASP.NET serves the Angular build from the same origin, so production-style local serving needs no permissive CORS policy.

## Query safeguards

- Exactly one SELECT over approved `analytics` tables; AST validation rejects multiple statements, write operations, system schemas, nested queries, CTEs, UNION, SELECT INTO, comments and locking clauses.
- Narrow SQL function allowlist: basic aggregates, date grouping, selected text functions and ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD.
- Restricted SELECT-only role plus explicit read-only transactions.
- 200-row result cap, truncation indicator, two-second statement timeout, lock timeout and an estimated plan-cost budget.
- Global API query rate limit, request cancellation, structured timing/status logs and bounded metadata storage.
- CSV cells beginning with formula-control characters are prefixed to reduce spreadsheet formula execution.

These are local-project boundaries, not a production security certification. The app has **no authentication, user/tenant isolation, enterprise audit service or production hosting**. Only loopback port 8080 is published. The included database passwords are synthetic local credentials; do not reuse them.

## Optional LLM drafting

Copy `.env.example` to `.env`, set `QUERY_MODE=llm` and configure `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`, then restart with `docker compose up --build`. Keys stay in the Python service. Provider calls can incur costs. Only the question and approved schema context are sent; the app does not send result rows to the model. Do not submit confidential questions.

Live-provider operation is not verified here. Valid, fenced and unsafe model responses are tested with mocks. There is no multi-agent orchestration framework, fine-tuning, model training, automatic repair loop or token accounting.

## Development without Docker

Use .NET SDK 8, Node 22, Python 3.12 and PostgreSQL 16.

1. Create a fresh `askdb` database and execute `db/init.sql` as its administrator. It creates `askdb_reader` and changes schema grants, so use an isolated local database.
2. Create/activate a Python venv; `pip install -r query_service/requirements.txt`.
3. Start `uvicorn main:app --app-dir query_service --port 8001`.
4. Set `ConnectionStrings__Analytics='Host=localhost;Database=askdb;Username=askdb_reader;Password=local-demo-reader'`, `PlannerUrl='http://localhost:8001'`, and optionally `WorkspacePath` to a writable local directory.
5. Run `dotnet run --project api --urls http://localhost:8080`.
6. In `web`, run `npm ci`, then `npm start`; open http://localhost:4200. The development proxy forwards `/api`.

On macOS/Linux use `export NAME='value'`; in PowerShell use `$env:NAME='value'`.

## Tests and builds

```sh
python3 -m pytest -q query_service/tests
dotnet build api -c Release
npm --prefix web ci
npm --prefix web run build
python3 scripts/smoke_test.py
```

The smoke test needs the app running in demo mode. Browser checks use Playwright:

```sh
cd web
npx playwright install chromium
cd ..
node scripts/browser_test.cjs
```

The browser test exercises query execution, filtering, charts, CSV download, saved-query reopening, pagination, invalid SQL, draft preview, history and mobile layout. It writes temporary QA screenshots to `.qa/`; these are not project deliverables.

GitHub Actions is configured for builds, Python tests, Compose smoke checks and browser checks. Use this directory as your repository root. The workflow has not been run on GitHub. See **docs/VERIFICATION.md** for actual results and limitations from creation.

## Development notes

Built with AI-assisted development and explicit validation of generated code. Architecture, executed checks, failure modes, and measured trade-offs are documented in the verification and maintenance guides.


## Maintenance workbench update

See [maintenance evidence](docs/MAINTENANCE_WORKBENCH.md) and [recorded history benchmark](METRICS.md) for HTTP/Playwright regressions, snapshot caching, timeout handling, and local release rehearsal.
