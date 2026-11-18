# BrgrByte project context

BrgrByte is a self-hosted, open-source network testing and reporting platform. A central dashboard coordinates distributed site agents that run open-source tools directly against authorized endpoints. One workstation may run both the dashboard and an agent; deployment should remain approachable on Windows and Linux.

BrgrByte's own code is GPL-2.0-only; it wraps independently licensed tools rather than replacing them. Nmap's additional terms and image redistribution are not yet cleared; do not imply that plain GPLv2 resolves them. See the README's license section.

## Product and UX

- The burger theme is intentional: build a burger by selecting test tools as patties and their settings as toppings; combos are preset configurations. Queueing starts separate tests, and taking a bite means viewing their results, not starting another test.
- Keep tool names, inputs, status, failure details, and reports clear alongside the themed language. Do not imply that a completed report proves the target is reachable.
- A burger uses one source and destination, but each selected tool is queued and reported independently. Partial submission and uncertain network outcomes must be visible; avoid silently retrying and duplicating tests.
- Preserve existing `NETWORKPATH_` environment variables, agent paths and service names, container identifiers, and database volume names for compatibility unless an explicit migration is requested.

## Architecture

- `frontend/`: React, TypeScript, Vite dashboard; `src/burger.ts` defines tools, combos, source eligibility, and per-tool submission.
- `backend/`: FastAPI, SQLAlchemy, PostgreSQL, Alembic migrations; SQLite is for isolated tests. `app/mtr_api.py` handles agent polling, job lifecycle, provisioning, and test creation.
- `agent/`: Python standard-library agent, packaged in a Linux container with MTR, iPerf3, SIPp, Nmap, ping, and traceroute. Agents advertise available tools, poll over authenticated HTTPS (HTTP only for localhost), and send results; test traffic goes directly to destinations.
- `start.py`: interactive Windows/Linux launcher for the dashboard, agent, or both. It generates secrets and enrolls agents without overwriting existing configuration.
- Administrators provision unique agent credentials, which are stored hashed. Operators can run bounded tests; viewers cannot. Preserve authorization, audit events, result persistence, and job expiry.
- Managed iPerf3 starts an unauthenticated, one-off receiver; restrict its port and require both reports. SIPp uses a bounded unauthenticated UDP UAC scenario, not RTP media testing.

## Implementation and validation

- Run only authorized probes and use validated, bounded inputs and fixed argument-vector subprocesses without a shell. Surface tool failures and retain useful partial output.
- Keep dashboard, API schemas/endpoints, agent capability advertisement and execution, container packages, tests, and directly related documentation aligned when adding or changing tools.
- Run backend checks from `backend/`: `pytest -q` and `ruff check app migrations tests ../agent ../start.py`. API tests use SQLite and tool subprocess tests use mocks.
- Run frontend checks from `frontend/`: `npm test` and `npm run build`. CI also builds the agent image and runs non-root loopback smoke tests.
- Docker Desktop agents use its Linux environment and may lack raw ICMP support; native Linux is preferred for host-level ICMP. Do not claim container, cross-host, or ARM64 validation without actually performing it.
- Consult `README.md`, `docs/GETTING_STARTED.md`, `docs/ARCHITECTURE.md`, and `docs/SECURITY.md` for current behavior and limitations.
