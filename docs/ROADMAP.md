# Roadmap

## Foundation delivered

- PostgreSQL data model and initial Alembic migration.
- FastAPI liveness/readiness, bootstrap administrator, expiring JWT login, protected inventory, overview, and site creation.
- Actor-attributed audit events for site creation.
- React/TypeScript control-center dashboard and Docker Compose packaging.
- Backend tests, lint configuration, frontend build checks, and CI workflow.

## Next increments

1. Validate the packaged agent on Debian ARM64; add credential rotation and durable result delivery.
2. Validate iPerf3 and SIPp on real networks; add UDP throughput, authenticated and custom SIP scenarios, and media testing.
3. Engine plugin interface and safe TCP, DNS, TLS, and receiver-backed UDP execution.
4. General test cancellation, real-time dashboard updates, scheduling/profiles, and exports.
5. User/role administration, expanded audit coverage, and production hardening.

Each network engine must report measured receiver/source results honestly and distinguish unavailable network access from successful dispatch.
