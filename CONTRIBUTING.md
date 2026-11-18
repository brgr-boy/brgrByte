# Contributing to brgrByte

Thank you for helping improve brgrByte. Code, documentation, bug reports, and
testing feedback are welcome. If you want to use brgrByte rather than change
it, start with the [getting started guide](docs/GETTING_STARTED.md).

## Proposing a change

1. For a bug report, describe the expected and actual behavior, the environment,
   and steps to reproduce it. Remove credentials and sensitive network details.
2. For a larger feature or behavior change, open an issue to discuss the approach.
3. Fork or clone the repository, create a branch, and make a focused change.
   Include tests and update documentation when behavior changes.
4. Run the relevant checks below and open a pull request describing the change,
   its motivation, and what you tested. Note any checks you could not run.

## Set up the project

You need Git, Python 3.12 or later for backend development, and Node.js 22 or
later for frontend development. Docker and the Compose plugin are needed for
the packaged control center and agent. On Windows, Docker Desktop runs the
agent in a Linux environment; network behavior differs from native Linux.

Clone the repository and change into its directory:

```sh
git clone https://github.com/brgr-boy/BrgrByte.git
cd BrgrByte
```

For a running API and dashboard, follow [getting started](docs/GETTING_STARTED.md)
to configure secrets and start the dashboard. The Compose database is private
to its Docker network. For a native API, use a separately reachable PostgreSQL
database, configure `BRGRBYTE_DATABASE_URL`, `BRGRBYTE_JWT_SECRET_KEY`,
`BRGRBYTE_ADMIN_USERNAME`, and `BRGRBYTE_ADMIN_PASSWORD`, then run
`alembic upgrade head` from `backend`. See [deployment](docs/DEPLOYMENT.md)
for configuration details. SQLite is intended only for isolated tests.

## Backend and agent checks

From the repository root, create a virtual environment and install the
development dependencies:

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python -m ruff check app migrations tests ..\agent ..\start.py
```

**Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check app migrations tests ../agent ../start.py
```

The backend tests use isolated SQLite and mock agent tool execution. They do
not validate real network paths. See the [testing guide](docs/TESTING_GUIDE.md)
for migration and container checks.

## Frontend checks and development server

From the repository root:

```sh
cd frontend
npm ci
npm test
npm run build
```

To work on the dashboard with a local API, add `http://localhost:5173` to the
API's comma-separated `BRGRBYTE_CORS_ORIGINS` and restart the API. Then,
from `frontend`, set `VITE_API_BASE_URL` to `http://localhost:8000` and start
Vite:

**Windows PowerShell**

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

**Linux**

```sh
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Network tools and licensing

Only test systems you are authorized to probe or load. Preserve bounded inputs,
agent permissions, and clear reporting when changing test tools. brgrByte wraps
independently licensed tools; review the [license and third-party notices](README.md#license-and-third-party-tools)
before changing dependencies or distributing an image. In particular, Nmap
redistribution clearance remains open. brgrByte's own code is licensed under
[GPL-2.0-only](LICENSE).
