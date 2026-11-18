#!/usr/bin/env python3
"""Start the brgrByte dashboard, site agent, or both."""

import argparse
import getpass
import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "agent"
MARKER = "Connected to the control center"


def docker_env():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("NETWORKPATH_", "POSTGRES_")) and key != "VITE_API_BASE_URL"
    }


def run(command, cwd=ROOT, capture=False):
    return subprocess.run(
        command,
        cwd=cwd,
        env=docker_env(),
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )


def compose(directory, *arguments, capture=False):
    return run(
        ["docker", "compose", "--env-file", str(directory / ".env"), *arguments],
        cwd=directory,
        capture=capture,
    )


def private_create(path, contents):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(contents)


def prompt(label, default=None):
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default or ""


def setup_dashboard():
    path = ROOT / ".env"
    if path.exists():
        print(f"Using existing {path}; it will not be overwritten.")
        return None
    print("Creating dashboard configuration. The password is not displayed while typing.")
    username = prompt("Administrator username", "admin")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", username):
        raise ValueError(
            "Administrator username must contain only letters, numbers, '.', '_' or '-'."
        )
    password = getpass.getpass("Administrator password (12+ URL-safe characters): ")
    if len(password) < 12 or not re.fullmatch(r"[A-Za-z0-9._~-]+", password):
        raise ValueError(
            "Password must be at least 12 characters and use letters, numbers, . _ ~ -."
        )
    if password != getpass.getpass("Confirm administrator password: "):
        raise ValueError("Passwords do not match.")
    contents = (
        f"NETWORKPATH_JWT_SECRET_KEY={secrets.token_urlsafe(48)}\n"
        f"NETWORKPATH_ADMIN_USERNAME={username}\n"
        f"NETWORKPATH_ADMIN_PASSWORD={password}\n"
        "NETWORKPATH_CORS_ORIGINS=http://localhost:8080,http://localhost:5173\n"
        "POSTGRES_USER=networkpath\n"
        f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
        "POSTGRES_DB=networkpath\n"
    )
    private_create(path, contents)
    print(f"Created {path}. Protect this file; it contains secrets.")
    return username, password


def validate_api_url(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid API URL.") from exc
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
        or any(char.isspace() or char in "$\\'\"" for char in url)
    ):
        raise ValueError("API URL must not contain credentials, query, fragment, or whitespace.")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError("Agent API URL must use HTTPS except for localhost.")
    return url.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_post(url, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url, data=json.dumps(data).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
            data = json.loads(response.read(65537))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            message = "Dashboard login failed; check the username and password."
        elif exc.code == 403:
            message = "Agent registration requires an administrator account."
        elif exc.code == 409:
            message = "That agent name already exists; choose a different name."
        else:
            message = f"Control center rejected the request (HTTP {exc.code})."
        raise RuntimeError(message) from exc
    except (urllib.error.URLError, OSError) as exc:
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        raise RuntimeError(f"Cannot connect to the control center: {reason}") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Control center returned an invalid response.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Control center returned an invalid response.")
    return data


def setup_agent(combined, dashboard_credentials=None):
    path = AGENT / ".env"
    if path.exists():
        print(f"Using existing {path}; it will not be overwritten.")
        return
    default = "http://localhost:8000" if combined else None
    url = validate_api_url(prompt("Control-center API URL", default))
    if dashboard_credentials is not None and url == "http://localhost:8000":
        username, password = dashboard_credentials
        print("Using the administrator account created during this setup.")
    else:
        username = prompt("Dashboard administrator username", "admin")
        password = getpass.getpass("Dashboard administrator password (input hidden): ")
    default_name = f"{socket.gethostname()[:75]}-{secrets.token_hex(3)}"
    name = prompt("Agent name", default_name).strip()
    if not name or len(name) > 120:
        raise ValueError("Agent name must be between 1 and 120 characters.")

    token = api_post(f"{url}/api/v1/auth/token", {"username": username, "password": password}).get(
        "access_token"
    )
    if not isinstance(token, str) or not token:
        raise RuntimeError("Control center returned an invalid login token.")

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    registration_attempted = False
    saved = False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            registration_attempted = True
            result = api_post(f"{url}/api/v1/agents", {"name": name}, token)
            credential = result.get("credential")
            if not isinstance(credential, str) or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{12}\.[A-Za-z0-9_-]+",
                credential,
            ):
                raise RuntimeError("Control center returned an invalid agent credential.")
            stream.write(f"NETWORKPATH_URL={url}\nNETWORKPATH_AGENT_CREDENTIAL={credential}\n")
        saved = True
    finally:
        if not saved:
            path.unlink(missing_ok=True)
        if registration_attempted and not saved:
            print(
                f"Agent '{name}' may have been created without saving its credential. "
                "Check the dashboard and revoke it if present before retrying.",
                file=sys.stderr,
            )
    print(f"Created {path}. Protect this file; it contains the agent credential.")


def verify_agent(since, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        running = compose(AGENT, "ps", "--status", "running", "-q", "agent", capture=True)
        if not running.stdout.strip():
            raise RuntimeError("Agent container is not running. Inspect: docker compose logs agent")
        logs = compose(AGENT, "logs", "--no-color", "--since", since, "agent", capture=True)
        lines = logs.stdout.splitlines()
        last_success = max((i for i, line in enumerate(lines) if MARKER in line), default=-1)
        last_error = max(
            (i for i, line in enumerate(lines) if re.search(r"\bERROR\b", line)), default=-1
        )
        if last_success > last_error:
            print("Agent connected to the control center. Refresh the Agents page.")
            return
        time.sleep(3)
    raise RuntimeError(
        "Agent started but did not confirm a connection. Check its URL, credential, TLS trust, "
        "Docker Desktop host networking, and logs in the agent directory: docker compose logs agent"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dashboard", "agent", "both"))
    args = parser.parse_args()
    mode = args.mode
    if mode is None:
        print("Choose a mode: 1) dashboard  2) agent  3) both")
        mode = {"1": "dashboard", "2": "agent", "3": "both"}.get(prompt("Selection"))
        if mode is None:
            raise ValueError("Select 1, 2, or 3.")
    if platform.system() not in ("Windows", "Linux"):
        raise ValueError("This launcher supports Windows and Linux.")
    if mode in ("agent", "both") and platform.system() == "Windows":
        print(
            "Windows: enable host networking in Docker Desktop settings. The agent runs in "
            "Docker's Linux environment; network paths and raw ICMP may differ or be unavailable."
        )
    run(["docker", "compose", "version"], capture=True)
    if run(["docker", "info", "--format", "{{.OSType}}"], capture=True).stdout.strip() != "linux":
        raise RuntimeError("Docker must be running with Linux containers.")
    dashboard_credentials = None
    if mode in ("dashboard", "both"):
        dashboard_credentials = setup_dashboard()
        compose(ROOT, "up", "-d", "--build", "--wait", "--wait-timeout", "240")
        print("Dashboard is running at http://localhost:8080")
    if mode in ("agent", "both"):
        setup_agent(mode == "both", dashboard_credentials)
        compose(AGENT, "up", "-d", "--build", "--wait", "--wait-timeout", "240")
        since = datetime.now(UTC).isoformat()
        verify_agent(since)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError, EOFError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStartup cancelled.", file=sys.stderr)
        sys.exit(130)
