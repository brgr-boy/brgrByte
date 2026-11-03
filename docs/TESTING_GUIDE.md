# Testing guide

## Backend

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
ruff check app migrations tests
```

The API tests use an isolated SQLite database and exercise health endpoints, login, authorization boundaries, site creation, and overview counts. They mock no live network calls because this foundation performs none.

To check the schema migration against PostgreSQL, provide a disposable PostgreSQL database through `NETWORKPATH_DATABASE_URL` and run `alembic upgrade head` from `backend`. The unit tests do not demonstrate connectivity to Raspberry Pi agents or validate network testing engines.

## Frontend

```powershell
cd frontend
npm ci
npm run build
```

The production build includes TypeScript project checks. CI runs backend tests/lint and the frontend production build. Docker image builds and hardware integration tests require environments not available in all development setups.
