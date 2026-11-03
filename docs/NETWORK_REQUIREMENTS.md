# Network requirements

## Current control-center foundation

- Browser to control center: TCP 8080 (dashboard) and TCP 8000 (API) for local Compose deployment.
- API to PostgreSQL: TCP 5432 on the private Docker Compose network. The database port is not published to the host.
- Production deployments should use HTTPS and should not expose the database to user or agent networks.

## Intended distributed-agent flows

- Agent to control center: outbound TLS WebSocket (planned; port depends on deployment/reverse-proxy configuration) for registration, heartbeat, commands, and results.
- Agent to agent: direct test traffic on explicitly configured ports/protocols. The data plane must not be tunneled through the control center.
- ICMP requires permitted ICMP echo traffic; UDP tests require a listening receiver and permitted UDP flows; SIP/RTP require explicitly opened signaling and media ranges. A firewall may block these even when management connectivity is healthy.

Agent listeners, per-engine port allocation, UDP receiver setup, and test traffic are not implemented in this phase. Do not infer end-to-end reachability from an agent's future management status.
