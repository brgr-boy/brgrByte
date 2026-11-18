# BrgrByte

BrgrByte is a self-hosted control center for running network tests from distributed sites and collecting their results in one place. It combines a web dashboard, a PostgreSQL-backed API, and site agents that package open-source testing tools.

Use it to investigate a network path, measure throughput between locations, or generate SIP call load from a site without manually collecting output from each host.

> **Project status:** The control center, agents, and test workflows are implemented, but live container execution and Raspberry Pi/ARM64 deployments have not yet been validated in this environment. See the [roadmap](docs/ROADMAP.md) and validate the setup in a lab before relying on it in production.

## What you can test

| Tool | Purpose | Current scope |
| --- | --- | --- |
| **MTR** | Investigate hops, latency, and packet loss along a path. | ICMP probes from an agent to a hostname or IP; per-hop and raw JSON reports. |
| **iPerf3** | Measure TCP throughput. | An agent tests an existing iPerf3 server, or another agent starts a temporary receiver. Managed tests save both source and receiver results. |
| **SIPp** | Generate SIP call load and report call outcomes. | Built-in unauthenticated UAC scenario over UDP; signaling only, with bounded call count, rate, concurrency, and duration. |
| **Nmap** | Check TCP ports on a host. | TCP connect scan of one hostname or IP and 1–100 explicitly selected ports; port states and service-name guesses are saved. |
| **Ping** | Check ICMP reachability and round-trip times. | 1–10 probes to a single host; output is saved even if no replies arrive. |
| **Traceroute** | Examine the path to a host. | Numeric UDP traceroute, up to 30 hops; firewalls may filter probes or responses. |

The dashboard also provides site and agent inventory, role-based access, agent credential provisioning and revocation, and saved test sessions. MTR or traceroute report collection does not guarantee that the destination responded; firewalls and ICMP rate limiting can affect measurements. SIPp does not measure RTP media quality. Only scan or probe systems you are authorized to test.

## How it works

![Central dashboard coordinating two site agents that test each other and external endpoints](docs/images/networkpath-architecture.svg)

The control center coordinates tests and stores reports; agents send test traffic directly to the destination. Agents run separately at each site, either in the provided Linux container or as a native Debian service. The agent image installs the tools during its build; the control-center image does not run them.

## Get started

Clone the repository and run the launcher from its root. Choose **dashboard**, **agent**, or **both** when prompted:

```powershell
# Windows (Python 3.11+ and Docker Desktop required)
py -3 start.py
```

```sh
# Linux (Python 3.11+ and Docker Engine with Compose required)
python3 start.py
```

Alternatively, pass `--mode dashboard`, `--mode agent`, or `--mode both`. On first setup, choose a dashboard administrator username and password. The launcher can use that account to register an agent automatically with a unique credential. Existing configuration files are never overwritten.

Windows agents run in Docker Desktop's Linux environment, not directly on the Windows network stack; host networking must be enabled and raw ICMP may be unavailable. Remote agents require a trusted HTTPS API endpoint. See the **[getting started guide](docs/GETTING_STARTED.md)** for setup, limitations, and your first report.

BrgrByte was previously named BrgrOps, Pathwise, and NetworkPath. Existing `NETWORKPATH_` environment variables, agent paths, container names, and database volume identifiers remain unchanged for compatibility.

In **Build & bite**, build a burger by selecting tool patties and configuring their toppings. The built-in Path and Service combos provide starting profiles. Run the selected tests, then **take a bite** to view their statuses and reports. Each tool creates a separate test using one source agent and destination; the results view shows recent tests from all burgers, not grouped orders. Combo choices replace the selected tools and reset their settings; review them before running tests.

## Documentation

- [Getting started](docs/GETTING_STARTED.md) — setup through the first saved report.
- [Agent installation](docs/AGENT_INSTALLATION.md) — container and native Debian setup.
- [Deployment](docs/DEPLOYMENT.md), [network requirements](docs/NETWORK_REQUIREMENTS.md), and [security](docs/SECURITY.md) — operational requirements and precautions.
- [Architecture](docs/ARCHITECTURE.md), [API reference](docs/API.md), and [roadmap](docs/ROADMAP.md) — design, endpoints, and planned work.
- [Testing guide](docs/TESTING_GUIDE.md) — development and validation commands.

## Development

Backend: Python 3.12+, `cd backend; pip install -r requirements-dev.txt; pytest -q; ruff check app migrations tests ..\agent ..\start.py`. The API requires `NETWORKPATH_DATABASE_URL`, `NETWORKPATH_JWT_SECRET_KEY`, `NETWORKPATH_ADMIN_USERNAME`, and `NETWORKPATH_ADMIN_PASSWORD`. Use PostgreSQL for local API development; SQLite is intended only for isolated tests.

Frontend: Node.js 22+, `cd frontend; npm ci; npm run build`. To use the Vite development server, allow `http://localhost:5173` in the API's CORS configuration, set `VITE_API_BASE_URL=http://localhost:8000`, and run `npm run dev`.
