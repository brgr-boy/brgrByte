# Roadmap

## Foundation delivered

- PostgreSQL data model and initial Alembic migration.
- FastAPI liveness/readiness, bootstrap administrator, expiring JWT login, protected inventory, overview, and site creation.
- Actor-attributed audit events for site creation.
- React/TypeScript control-center dashboard and Docker Compose packaging.
- Backend tests, lint configuration, frontend build checks, and CI workflow.

## Next increments

1. Agent identity and credential issuance/rotation; authenticated outbound WebSocket; heartbeat, health metrics, reconnect, and systemd installer for Debian 13 ARM64.
2. Engine plugin interface and safe ICMP, TCP, DNS, TLS, and receiver-backed UDP execution with unit tests.
3. Persisted test orchestration, cancellation/timeouts, result ingestion, and real-time dashboard updates.
4. iPerf3 execution and analytics, followed by SIPp integration.
5. User/role administration, audit trail, scheduling/profiles, exports, and production hardening.

Each network engine must report measured receiver/source results honestly and distinguish unavailable network access from successful dispatch.
