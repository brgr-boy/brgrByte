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

Agent registration, test creation/execution/cancellation, results, WebSockets, and reporting endpoints are not available yet. `GET /health/live` and `GET /health/ready` expose only service availability, not administrative functionality.
