# Testing guide

## Backend

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
ruff check app migrations tests ..\agent ..\start.py
```

The API tests use an isolated SQLite database and exercise inventory, authorization, test orchestration, agent identity, revocation, and result persistence. Agent subprocess tests mock the tools; they do not prove live network measurements.

To check the schema migration against PostgreSQL, provide a disposable PostgreSQL database through `NETWORKPATH_DATABASE_URL` and run `alembic upgrade head` from `backend`. The unit tests do not demonstrate connectivity to Raspberry Pi agents or validate network testing engines.

## Frontend

```powershell
cd frontend
npm ci
npm test
npm run build
```

The production build includes TypeScript project checks. CI builds the agent image, checks the pinned Nmap package versions, and runs loopback MTR, iPerf3, SIPp, Nmap, ping, and traceroute smoke tests as its non-root user with the documented capabilities. PostgreSQL concurrency and real network and ARM64 hardware integration require additional live environments.
