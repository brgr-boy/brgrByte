# Security

- Set unique, randomly generated administrator, database, and JWT signing secrets before starting Compose. Never commit `.env` or use example placeholders outside local setup.
- Passwords use Argon2 hashing. API access tokens are signed with HS256, expire after a configurable interval, and are kept in browser memory only (a page refresh requires sign-in again).
- Inventory APIs require authentication. The viewer role cannot create sites; role enforcement is server-side.
- Site creation writes an actor-attributed audit event in the same database transaction as the change.
- PostgreSQL is private to the Compose network. The API process runs as a non-root container user.
- Configure exact browser origins using `BRGRBYTE_CORS_ORIGINS`. Put production traffic behind TLS termination and restrict management port access.
- Agent credentials are generated individually, stored as SHA-256 hashes, and can be revoked by an administrator. Agent provisioning, revocation, and test creation are audited.
- Agents accept bounded MTR, iPerf3, SIPp, Nmap, ping, and traceroute jobs and use argument-vector subprocesses without a shell. Nmap is limited to one host and 100 explicitly chosen TCP ports. Operators can scan, probe, or generate load against any hostname or IP reachable from an agent; restrict operator access and agent network placement accordingly. Agent management traffic requires HTTPS except to localhost.
- iPerf3 servers are unauthenticated and may saturate a network link. A managed receiver listens on all interfaces; restrict the chosen port to authorized test hosts. Another client could consume the one-off receiver.
- The packaged Linux agent uses host networking and `NET_RAW`; its MTR packet helper is setuid root inside the container. Restrict Docker and agent-host access, protect its `.env` file, and do not run it privileged.
- Existing administrator passwords are not overwritten on startup. Rotate credentials through a future dedicated administrative operation; until then, bootstrap password changes apply only to a newly created account.

This project does not yet provide user self-service, rate limiting, comprehensive audit coverage for authentication, TLS certificate automation, in-place agent credential rotation, or production-grade account recovery. Revocation does not stop a subprocess already running.
