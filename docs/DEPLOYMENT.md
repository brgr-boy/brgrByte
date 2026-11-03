# Control-center deployment

## Windows 11 with Docker Desktop

1. Install Docker Desktop with its WSL2 backend and enable Docker Compose.
2. Clone the repository and copy `.env.example` to `.env`.
3. Replace all secret placeholders. Use separate random values for the database password, JWT signing key, and administrator password. Keep `.env` private; it is excluded by `.gitignore`.
4. In PowerShell, from the repository root, run `docker compose up --build`.
5. Browse to `http://localhost:8080`, sign in using the configured administrator username/password, and verify `http://localhost:8000/health/ready`.

The frontend is published on port 8080 and the API on port 8000. PostgreSQL is on the private Compose network only. The API applies Alembic migrations on container startup and bootstraps the configured administrator if that username does not already exist. Changing bootstrap credentials does not rotate or reset an existing account's password.

`docker compose down` stops containers but preserves the PostgreSQL named volume. Back up the volume before upgrades. Destructive volume removal is intentionally not part of the standard instructions.

## Production considerations

Terminate TLS at a trusted reverse proxy, update `NETWORKPATH_CORS_ORIGINS` and `VITE_API_BASE_URL`, restrict exposed ports, store secrets in a managed secret store, and secure database backups. This phase is an initial deployment foundation, not a production-hardened identity or certificate-management solution.
