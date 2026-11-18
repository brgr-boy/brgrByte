# API reference

Base prefix: `/api/v1`. Except for health checks and login, endpoints require `Authorization: Bearer <access_token>`. Tokens are signed JWTs with configured expiry. API schemas are also published by FastAPI at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | Database readiness |
| `POST` | `/api/v1/auth/token` | Exchange JSON `username` and `password` for an access token |
| `GET` | `/api/v1/users/me` | Return the authenticated user's ID, username, and role |
| `GET` | `/api/v1/overview` | Return site, agent, online-agent, and active-test counts |
| `GET` | `/api/v1/sites` | List sites |
| `POST` | `/api/v1/sites` | Create a site (`admin` and `operator` roles) |
| `GET` | `/api/v1/agents` | List registered agent inventory |
| `POST` | `/api/v1/agents` | Administrator creates an agent; response contains its one-time credential |
| `POST` | `/api/v1/agents/{id}/revoke` | Administrator revokes the credential and cancels outstanding jobs |
| `POST` | `/api/v1/tests/mtr` | Operator or administrator queues a bounded MTR test |
| `POST` | `/api/v1/tests/iperf3` | Queue TCP throughput test to an external server or a destination agent |
| `POST` | `/api/v1/tests/sipp` | Queue a bounded SIPp basic UAC call-load test |
| `POST` | `/api/v1/tests/nmap` | Queue a single-host TCP connect scan of 1–100 distinct `ports` (default `[22, 80, 443]`) |
| `POST` | `/api/v1/tests/ping` | Queue ICMP ping to a single host with `count` from 1–10 (default 4) |
| `POST` | `/api/v1/tests/traceroute` | Queue a single-host UDP traceroute, up to 30 hops |
| `POST` | `/api/v1/tests/dns` | Query a DNS name using `server` (IPv4/IPv6 address, default `8.8.8.8`) and `record_type` (default `A`) |
| `GET` | `/api/v1/tests` | List the latest 100 sessions and persisted results |
| `POST` | `/api/v1/agent/poll` | Agent heartbeat and claim of queued work |
| `POST` | `/api/v1/agent/jobs/{id}/result` | Agent submits the result of its own running job |
| `POST` | `/api/v1/agent/jobs/{id}/ready` | Destination agent confirms its iPerf3 receiver is listening |

The agent endpoints use the provisioned agent credential as a bearer token, not a user JWT. Do not expose credentials in URLs or logs. `GET /health/live` and `GET /health/ready` expose only service availability, not administrative functionality. General cancellation, WebSockets, and export endpoints are not available.

The test endpoints require `source_agent_id` and `target` (a single hostname or IP, not a subnet; DNS requires a DNS name and permits underscores). Only administrators and operators can create tests. Nmap records port states and port-based service guesses; no version detection is performed. Ping failures can retain output, and a completed traceroute does not necessarily mean the target responded.

DNS accepts record types `A`, `AAAA`, `CNAME`, `MX`, `NS`, `SOA`, and `TXT`. The server must be an unscoped IP address, not a hostname, and is queried on port 53. `NOERROR` means a response was received, not necessarily that the requested record exists; inspect `answer_count` and the saved output. Other response codes, timeouts, missing tools, and malformed responses fail the test. The answer count includes all records in the answer section, including CNAMEs.
