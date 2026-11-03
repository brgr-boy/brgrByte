# NetworkPath

NetworkPath is a self-hosted control center for coordinating network tests across distributed sites. The initial foundation provides a PostgreSQL-backed API, authenticated site and agent inventory, and a responsive operations dashboard. Agents and test execution are planned next; this release does not claim that tests can be run yet.

## Run the control center

Requirements: Docker Desktop with Compose, and a browser. Copy `.env.example` to `.env`, then set unique values for `POSTGRES_PASSWORD`, `NETWORKPATH_JWT_SECRET_KEY` (at least 32 characters), and `NETWORKPATH_ADMIN_PASSWORD` (at least 12 characters). The example contains placeholders, not usable production secrets.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) and sign in with `NETWORKPATH_ADMIN_USERNAME` and `NETWORKPATH_ADMIN_PASSWORD` from `.env`. The API is available at [http://localhost:8000](http://localhost:8000); interactive API documentation is at `/docs`. PostgreSQL is not published to the host. To stop the services while retaining data, run `docker compose down`; the named database volume persists until explicitly removed.

## Current capabilities

- Bootstrap an administrator from environment configuration.
- Authenticate with signed, expiring JWT access tokens; passwords are Argon2-hashed.
- View site and agent inventory and aggregate counts behind authenticated APIs.
- Create sites and enforce basic viewer/operator/admin role boundaries.
- Record site-creation audit events without placing credentials in audit details.
- Persist sites, agents, users, test-session state, and results in PostgreSQL through Alembic migrations.
- Operate a responsive dashboard with live inventory, agent availability, and honest empty states when agents or results do not yet exist.

## Development

Backend: Python 3.12+, `cd backend; pip install -r requirements-dev.txt; pytest -q; ruff check app migrations tests`. The API requires `NETWORKPATH_DATABASE_URL`, `NETWORKPATH_JWT_SECRET_KEY`, `NETWORKPATH_ADMIN_USERNAME`, and `NETWORKPATH_ADMIN_PASSWORD`. For local API development use PostgreSQL, or use SQLite only for isolated tests.

Frontend: Node.js 22+, `cd frontend; npm ci; npm run build`. To use the Vite development server, configure the API to allow `http://localhost:5173`, set `VITE_API_BASE_URL=http://localhost:8000`, and run `npm run dev`.

## Architecture and operations

See [architecture](docs/ARCHITECTURE.md), [deployment](docs/DEPLOYMENT.md), [agent installation](docs/AGENT_INSTALLATION.md), [network requirements](docs/NETWORK_REQUIREMENTS.md), [testing guide](docs/TESTING_GUIDE.md), [API reference](docs/API.md), [security](docs/SECURITY.md), and the [roadmap](docs/ROADMAP.md).
