# Agent installation

The native Debian 13 ARM64 agent, systemd service, registration flow, and installer have not been implemented yet. Do not install an unofficial agent or treat an inventory row as a connected agent.

The planned Raspberry Pi 5 deployment uses independently configured `pi-dc-lab` and `pi-branch-lab` identities, unique per-agent credentials, an outbound authenticated WebSocket to the control center, and direct peer traffic for tests. No IP addresses are hardcoded. See [network requirements](NETWORK_REQUIREMENTS.md) for the intended firewall boundaries.

Once agent software is released, installation instructions will include package verification, least-privilege service configuration, credential rotation, and systemd health/restart behavior.
