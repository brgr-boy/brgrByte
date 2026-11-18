# Agent installation

## Packaged Linux container

The cross-platform launcher in [getting started](GETTING_STARTED.md) can configure and start the agent automatically. On Windows it runs inside Docker Desktop's Linux environment, with different network paths and limited raw ICMP support; enable Docker Desktop host networking and use native Linux for host-level ICMP measurements.

The agent image includes Python, Debian's `mtr-tiny`, `iperf3`, `sip-tester`, `nmap`, `iputils-ping`, `traceroute`, and `dnsutils` (providing `dig`) packages, and CA certificates. Building it downloads these packages; their source and binaries are not vendored in this repository. The image supports the architectures provided by the Python base image and Debian's packages, including Linux ARM64, but has not yet been validated on Raspberry Pi hardware. See `/usr/share/doc/<package>/copyright` in the image for licensing and source information. Rebuild and restart an existing image to install new tools.

brgrByte wraps these separately licensed tools; it invokes them and collects their output. It uses the [Nmap Security Scanner](https://nmap.org/) for TCP scans. Redistribution of a brgrByte image containing Nmap has not been cleared: see the [license](../README.md#license) section before distributing one. The container pins Debian `nmap` and `nmap-common` to `7.95+dfsg-3`; a build fails if that version is no longer available. Update the pin and notices together after review. Native installations can use a different version and require their own license review.

1. Install Docker Engine and the Compose plugin on the Linux site host. Obtain a copy of this repository on the host. In the Order Window, register a separate Chef on the **Chefs** page as an administrator and copy its one-time credential. Each site needs its own credential.
2. From the repository's `agent` directory, create a private `.env` file and edit it with the control-center URL and credential. Do not put credentials in the repository or shell history:

   ```sh
   cd agent
   umask 077
   touch .env
   chmod 600 .env
   # Edit .env with a text editor, then add:
   # NETWORKPATH_URL=https://control-center.example
   # NETWORKPATH_AGENT_CREDENTIAL=<credential-from-dashboard>
   ```

   Use a trusted HTTPS endpoint accessible from the agent host. HTTP is allowed only for localhost. To trust a private CA, build a custom image that installs its CA certificate; do not disable TLS verification.
3. Run `docker compose up -d --build`. Check `docker compose logs -f agent` and refresh **Chefs** in the Order Window. The site agent should show as online with MTR available. To verify actual ICMP probe permissions, run:

   ```sh
   docker compose run --rm --no-deps --entrypoint mtr agent \
     --json --report -n --report-cycles 1 --max-ttl 2 127.0.0.1
   ```

   A JSON report showing the `127.0.0.1` hop with less than 100% loss verifies that MTR can probe inside this container; it does not verify connectivity to other destinations. Check Docker logs and firewall/host security policies if this command fails.
4. In **Build & bite**, select the MTR patty and a Chef, then place the order. Choose **Take a bite** and refresh to see the saved report. Run `docker compose down` to stop the Chef. To update it or MTR, update the checkout and run `docker compose build --pull --no-cache` followed by `docker compose up -d`.

To run iPerf3, choose either an existing external iPerf3 server or another Chef as the receiver. For a Chef receiver, enter its actual reachable hostname or IP (not necessarily its reported OS hostname); the receiver is started temporarily on the requested port. Open that TCP port between sites. iPerf3's server is unauthenticated, so restrict network access to trusted test hosts. Another client connecting first can consume the one-off receiver. iPerf3 can saturate a link.

SIPp uses its built-in unauthenticated UAC scenario over UDP: it sends INVITE, waits for a successful response, ACKs and ends the call. Configure an endpoint that accepts this flow and the requested URI user; this is signaling-only and does not measure RTP audio quality. The job stops after 80 seconds: choose a call count and rate that allow enough time for calls to complete. SIPp may use the host's default local IP in SIP headers, which must be reachable by the SIP endpoint. Do not run call load against systems without authorization.

Nmap uses a TCP connect scan against a single host and up to 100 selected ports, without service-version detection. Ping uses 1–10 ICMP probes, and traceroute uses UDP with up to 30 hops. Scan and probe only authorized systems. Ping requires suitable ICMP permissions; Docker Desktop may not support ICMP from the agent container. A completed traceroute does not imply the destination replied.

DNS uses `dig` to query a selected DNS server on port 53, defaulting to `8.8.8.8`. A `NOERROR` response can have no answers; inspect the answer count and output. It does not configure the resolver used by other tools.

The container uses Linux host networking, so probes originate in the host network namespace rather than traversing a Docker bridge. There are no published ports. The process runs as UID 10001, with all container capabilities dropped except `NET_RAW`; only the bundled `mtr-packet` helper is setuid root so it can acquire that capability. Do not add `no-new-privileges` or remove `NET_RAW` without providing another supported way for MTR to send probes. This setup may not work under rootless Docker, user namespaces, or restrictive security policies. Do not use `--privileged`. Docker access and the `.env` file grant access to the agent credential.

## Native Debian installation

The agent is a Python standard-library process for Linux hosts. The example below targets Debian with systemd; the service account must be able to run the distribution's `mtr` and its `mtr-packet` helper with the permissions required for ICMP probes. No agent listener is required. A live Debian ARM64 deployment has not yet been validated.

1. Deploy the Order Window behind a trusted HTTPS reverse proxy. Register a Chef on the **Chefs** page as an administrator and copy its one-time credential. Each site needs a distinct agent and credential.
2. On the site host, install `python3`, `mtr-tiny`, `iperf3`, `sip-tester`, `nmap`, `iputils-ping`, `traceroute`, and `dnsutils` using the system package manager. Copy this repository's `agent/networkpath_agent.py` and `agent/networkpath-agent.service` to the host. For example, from a checkout on the host:

   ```sh
   sudo apt update
   sudo apt install python3 mtr-tiny iperf3 sip-tester nmap iputils-ping traceroute dnsutils
   sudo useradd --system --no-create-home --shell /usr/sbin/nologin networkpath
   sudo install -d -m 755 /opt/networkpath
   sudo install -m 644 agent/networkpath_agent.py /opt/networkpath/networkpath_agent.py
   sudo install -m 644 agent/networkpath-agent.service /etc/systemd/system/networkpath-agent.service
   sudo install -d -m 700 /etc/networkpath
   sudo install -m 600 /dev/null /etc/networkpath/agent.env
   ```

3. Edit `/etc/networkpath/agent.env` as root, inserting the actual HTTPS URL and the one-time credential. Do not put credentials in the repository or shell history:

   ```text
   NETWORKPATH_URL=https://control-center.example
   NETWORKPATH_AGENT_CREDENTIAL=<credential-from-dashboard>
   ```

   The URL must use HTTPS except for localhost, and the host must trust the reverse proxy's certificate. Protect the file and host: systemd service environment variables are not a dedicated secrets vault.
4. Run `sudo systemctl daemon-reload`, then `sudo systemctl enable --now networkpath-agent`. Inspect `sudo systemctl status networkpath-agent` and `sudo journalctl -u networkpath-agent` for errors. Refresh **Chefs** in the Order Window to check connectivity and MTR availability.
5. In Build & bite, select the MTR patty and online agent, enter a hostname or IP address, and run the test. Choose Take a bite and refresh to see the saved report. The MTR package must support JSON output. If its helper cannot send probes, the test reports an error; consult the distribution's MTR permissions and firewall configuration rather than running the whole agent as root.

The agent retries result delivery while running, but pending results are not durable across agent restarts. A lost or expired job becomes `TIMEOUT`; submit a new test. Revoke a compromised credential from the **Chefs** page in the Order Window, then create a new agent identity. Rotation in place is not implemented. Revocation cancels associated queued/running jobs but cannot interrupt an MTR process already running on the host.
