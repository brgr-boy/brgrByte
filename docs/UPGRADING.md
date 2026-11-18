# Upgrading existing installations

The new release uses brgrByte-prefixed settings, agent files, service names, and container images. Compatibility handling keeps existing dashboard `.env` files, agent credentials, and PostgreSQL data usable during the transition.

## Dashboard and database

Keep your existing root `.env`; do not replace it with `.env.example`. The application accepts the previous environment-variable prefix, and existing PostgreSQL username and database values in `.env` continue to be used. New installations should use the current names from `.env.example`.

The existing PostgreSQL volume is reused by default for the standard Compose project. If you previously used a custom Compose project name, set `BRGRBYTE_POSTGRES_VOLUME` in `.env` to the exact volume name from `docker volume ls`. Stop and recreate the containers without deleting volumes:

```sh
docker compose down
docker compose up -d --build
```

Never use `docker compose down -v` during this migration. It deletes the database volume.

## Packaged agent

Existing agent `.env` files continue to work. The new image accepts both current and previous agent setting names, and the launcher preserves an existing agent configuration.

## Native Debian agent

Install the new `brgrbyte-agent` service using the steps in [agent installation](AGENT_INSTALLATION.md#native-debian-installation). Copy the existing `/etc/networkpath/agent.env` to `/etc/brgrbyte/agent.env` and keep its permissions restricted. The new service accepts the old variable names while you transition.

Stop and disable the old service before starting the new one; do not remove its configuration until the new service has been verified:

```sh
sudo systemctl disable --now networkpath-agent
sudo systemctl daemon-reload
sudo systemctl enable --now brgrbyte-agent
sudo systemctl status brgrbyte-agent
```

The old service may be removed after the new agent is online and reporting its capabilities. The migration does not change agent credentials or saved test results.
