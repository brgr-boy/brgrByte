# BrgrByte

BrgrByte is a self-hosted wrapper and control center for running network tests from distributed sites and collecting their results in one place. It combines a web dashboard, a PostgreSQL-backed API, and site agents that invoke independently developed network-testing tools and collect their output. BrgrByte is not a replacement implementation of those tools.

Created by **Anthony Sylvester** ([brgr-boy](https://github.com/brgr-boy)), BrgrByte aims to empower network operators with an easy-to-use tool for performing common network tests.

Use it to investigate a network path, measure throughput between locations, or generate SIP call load from a site without manually collecting output from each host.

> **Project status:** The control center, agents, and test workflows are implemented, but live container execution and Raspberry Pi/ARM64 deployments have not yet been validated in this environment. See the [roadmap](docs/ROADMAP.md) and validate the setup in a lab before relying on it in production.

## What you can test

| Tool | Purpose | Current scope |
| --- | --- | --- |
| **Ping** | Check ICMP reachability and round-trip times. | 1–10 probes to a single host; output is saved even if no replies arrive. |
| **Traceroute** | Examine the path to a host. | Numeric UDP traceroute, up to 30 hops; firewalls may filter probes or responses. |
| **DNS (dig)** | Query a DNS server for records. | Choose an IPv4 or IPv6 DNS server (default `8.8.8.8`) and record type; response status and answers are saved. |
| **MTR** | Investigate hops, latency, and packet loss along a path. | ICMP probes from an agent to a hostname or IP; per-hop and raw JSON reports. |
| **Nmap** | Check TCP ports on a host. | TCP connect scan of one hostname or IP and 1–100 explicitly selected ports; port states and service-name guesses are saved. |
| **iPerf3** | Measure TCP throughput. | An agent tests an existing iPerf3 server, or another agent starts a temporary receiver. Managed tests save both source and receiver results. |
| **SIPp** | Generate SIP call load and report call outcomes. | Built-in unauthenticated UAC scenario over UDP; signaling only, with bounded call count, rate, concurrency, and duration. |

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

## Contributing

Contributions to code, documentation, and testing are welcome. See the [contributing guide](CONTRIBUTING.md) for development setup, checks, and pull requests.

## License and third-party tools

BrgrByte's own code is licensed under the [GNU General Public License, version 2 only](LICENSE) (GPL-2.0-only). The separately developed tools and dependencies retain their own licenses; BrgrByte's license does not replace them. The agent image installs Debian packages during build rather than vendoring their source. Consult each installed package's `/usr/share/doc/<package>/copyright` and applicable license terms when distributing images or binaries.

BrgrByte uses the [Nmap Security Scanner](https://nmap.org/) to perform TCP port scans. Its agent specifically executes Nmap and parses its output. Nmap's terms are not plain GPLv2: the [Debian trixie package license](https://sources.debian.org/src/nmap/7.95%2Bdfsg-3/debian/copyright/) describes additional conditions, including its interpretation of applications that execute Nmap and parse results, and states that its covered work cannot be combined with plain GPL software without the additional terms. The upstream [Nmap Public Source License](https://nmap.org/npsl/) likewise has additional terms and has not been through OSI certification. These texts are not interchangeable. The agent image pins `nmap` and `nmap-common` to Debian `7.95+dfsg-3`; native installations and modified images may use different versions.

The [third-party notices](third-party-notices/README.md) include a copy of the Nmap 7.95 source package's license for reference. It is not a substitute for the notices applicable to the exact version in a distributed release.

**Nmap redistribution is not yet cleared.** GPLv2 alone does not establish that distributing a BrgrByte image containing Nmap complies with Nmap's terms. Obtain written clarification or permission from the Nmap Project, or consult qualified counsel, before distributing such an image. Review source availability, attribution, and the other tools' and dependencies' licenses separately. This is not a legal opinion.
