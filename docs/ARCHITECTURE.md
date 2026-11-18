# Architecture

The Docker Compose control center consists of a React frontend, FastAPI API, and PostgreSQL. A separately installed site agent polls the API over outbound HTTPS using its own credential; MTR probe traffic goes directly from the agent to the target, not through the control center. HTTP is allowed by the agent only for localhost. The production reverse proxy and its TLS certificate are the deployer's responsibility.

The site agent can run in its own Linux container image, which packages Debian MTR, iPerf3, SIPp, Nmap, ping, traceroute, and dig alongside the agent. The provided Compose configuration uses host networking and grants the raw-socket capability needed for ICMP probes. The control center does not execute the probes.

An administrator provisions a credential once; only its SHA-256 digest is stored. An agent advertises MTR availability and polls for work. Operators create bounded MTR jobs against hostnames or IPs, and an agent atomically claims its own queued jobs. The agent invokes a fixed argument vector without a shell, parses MTR JSON, and sends either measurements or an error. The API persists the result and terminal state together. The dashboard displays recent reports and raw JSON.

Jobs move from `CREATED` to `RUNNING` to `COMPLETED` or `FAILED`. For a managed iPerf3 receiver, the destination claims the job, starts a one-off server and confirms its own listening socket before the job becomes `READY` and the source can claim it. Both agent reports are required for completion. An external iPerf3 server does not have a managed receiver report. The operator supplies the destination's reachable address; readiness does not establish that the address resolves to that agent or prevent another client using the unauthenticated receiver.

A queued job expires after five minutes, and a preparing, ready or running job after 150 seconds; expiration is applied on subsequent API activity. Revocation cancels outstanding jobs but does not stop already running processes. MTR is limited to 90 seconds and 1–20 cycles; `COMPLETED` means a report was collected, not that the destination responded. Intermediary ICMP rate limiting and firewalls can distort hop loss. iPerf3 is TCP-only and runs for 1–60 seconds. SIPp runs a basic UDP UAC scenario without authentication, up to 1000 calls, 20 calls per second, 100 concurrent calls, and an 80-second timeout. Calls must all succeed for the session to complete successfully.

Nmap performs TCP connect scans of one host and at most 100 selected ports, with an 80-second host timeout. Ping sends up to 10 ICMP probes and retains output on failure. Traceroute sends UDP probes with a 30-hop limit. These tools have 90-second subprocess timeouts; traceroute completion means output was collected, not that the target replied.

DNS runs a bounded `dig` query against a configured server IP (default `8.8.8.8`), saving the response status and output. A `NOERROR` response may contain no answers; it does not prove a record exists. DNS settings do not change the resolver used by other tests.

This first transport uses polling rather than the earlier planned WebSocket. Agent credential rotation, persistent agent-side result queues, scheduling, exports, UDP iPerf3, authenticated/custom SIP scenarios, RTP media testing, and real-time updates remain future work.
