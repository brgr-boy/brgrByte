# Network requirements

- Browser to control center: TCP 8080 (dashboard) and TCP 8000 (API) for local Compose. Production deployments should terminate HTTPS at a trusted reverse proxy and restrict management access.
- API to PostgreSQL: TCP 5432 on the private Docker Compose network. The database port is not published to the host.
- Agent to control center: outbound HTTPS to the reverse proxy; no inbound agent management listener is needed. The agent trusts the system certificate store.
- Agent to destination: MTR uses ICMP probes and needs appropriate host permissions and network firewall rules. A connected agent does not imply destination reachability; routers may rate-limit or filter probes.
- The provided agent container uses Linux host networking so reports reflect the site's network namespace. It needs the `NET_RAW` capability and a setuid MTR packet helper; it exposes no inbound ports. Docker Desktop host networking differs from native Linux and is not a substitute for a site agent.
- iPerf3 TCP requires the selected receiver port (default 5201) reachable from the source. Agent-managed receivers listen on all interfaces during the test and are unauthenticated; restrict access with host and network firewalls. External servers must already be running.
- SIPp sends SIP signaling over UDP to the selected destination port (default 5060) and needs return signaling access to the agent. SIP headers advertise the local IP selected by SIPp; it must be reachable from the endpoint. No RTP media traffic is generated.
- Nmap opens TCP connections to selected ports. Firewalls and filtering affect port states. Ping uses ICMP echo; traceroute sends UDP probes and relies on ICMP replies. The agent's host must permit these packets and replies. Docker Desktop may prevent raw ICMP ping.
