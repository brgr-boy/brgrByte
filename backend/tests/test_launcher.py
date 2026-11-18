import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location(
    "networkpath_start", Path(__file__).resolve().parents[2] / "start.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize(
    "url",
    [
        "http://remote:8000",
        "https://user:pass@example.org",
        "https://host?key=value",
        "https://host/$SECRET",
        "https://host:99999",
    ],
)
def test_invalid_agent_urls_rejected(url):
    with pytest.raises(ValueError):
        launcher.validate_api_url(url)


def test_valid_agent_urls():
    assert launcher.validate_api_url("http://localhost:8000/") == "http://localhost:8000"
    assert launcher.validate_api_url("https://control.example/api") == "https://control.example/api"


def test_dashboard_config_is_private_and_never_overwritten(tmp_path):
    with (
        patch.object(launcher, "ROOT", tmp_path),
        patch.object(launcher, "prompt", return_value="admin"),
        patch.object(launcher.getpass, "getpass", side_effect=["safe-password-123"] * 2),
    ):
        launcher.setup_dashboard()
        config = (tmp_path / ".env").read_text()
        assert "NETWORKPATH_ADMIN_PASSWORD=safe-password-123" in config
        assert "replace-with" not in config
        if os.name != "nt":
            assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
        with patch.object(launcher, "prompt", side_effect=AssertionError("unexpected prompt")):
            launcher.setup_dashboard()
        assert (tmp_path / ".env").read_text() == config


def test_agent_config_saved_without_disclosing_secret(tmp_path, capsys):
    secret = "12345678-1234-1234-1234-123456789abc.secret_123"
    with (
        patch.object(launcher, "AGENT", tmp_path),
        patch.object(launcher, "prompt", side_effect=["http://localhost:8000", "test-agent"]),
        patch.object(
            launcher,
            "api_post",
            side_effect=[{"access_token": "temporary"}, {"credential": secret}],
        ) as api,
        patch.object(launcher.getpass, "getpass", side_effect=AssertionError("unexpected prompt")),
    ):
        launcher.setup_agent(True, ("admin", "chosen-password"))
        assert secret in (tmp_path / ".env").read_text()
        assert secret not in capsys.readouterr().out
        assert api.call_args_list[0].args[1] == {"username": "admin", "password": "chosen-password"}
        assert api.call_args_list[1].args[1] == {"name": "test-agent"}
        launcher.setup_agent(True)
        assert api.call_count == 2


def test_remote_agent_prompts_for_admin_and_does_not_reuse_local_credentials(tmp_path):
    with (
        patch.object(launcher, "AGENT", tmp_path),
        patch.object(
            launcher, "prompt", side_effect=["https://remote.test", "remote-admin", "site"]
        ),
        patch.object(launcher.getpass, "getpass", return_value="remote-password"),
        patch.object(
            launcher,
            "api_post",
            side_effect=[
                {"access_token": "token"},
                {"credential": "12345678-1234-1234-1234-123456789abc.secret"},
            ],
        ) as api,
    ):
        launcher.setup_agent(True, ("local-admin", "local-password"))
        assert api.call_args_list[0].args[1] == {
            "username": "remote-admin",
            "password": "remote-password",
        }


def test_failed_registration_cleans_config_and_warns(tmp_path, capsys):
    with (
        patch.object(launcher, "AGENT", tmp_path),
        patch.object(launcher, "prompt", side_effect=["http://localhost:8000", "branch"]),
        patch.object(
            launcher, "api_post", side_effect=[{"access_token": "token"}, RuntimeError("offline")]
        ),
    ):
        with pytest.raises(RuntimeError, match="offline"):
            launcher.setup_agent(True, ("admin", "password"))
        assert not (tmp_path / ".env").exists()
        assert "may have been created" in capsys.readouterr().err


def test_registration_with_real_api(client, tmp_path):
    def api_post(url, data, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        path = launcher.urlsplit(url).path
        response = client.post(path, json=data, headers=headers)
        assert response.status_code in (200, 201)
        return response.json()

    with (
        patch.object(launcher, "AGENT", tmp_path),
        patch.object(launcher, "prompt", side_effect=["http://localhost:8000", "branch"]),
        patch.object(launcher, "api_post", side_effect=api_post),
    ):
        launcher.setup_agent(True, ("admin", "test-password-long-enough"))
    credential = (tmp_path / ".env").read_text().split("NETWORKPATH_AGENT_CREDENTIAL=")[1].strip()
    result = client.post(
        "/api/v1/agent/poll",
        headers={"Authorization": f"Bearer {credential}"},
        json={
            "hostname": "branch",
            "os_name": "Linux",
            "architecture": "x86_64",
            "mtr_available": True,
        },
    )
    assert result.status_code == 200
    assert result.json() == {"job": None}


def test_no_admin_credentials_saved_in_agent_file(tmp_path):
    with (
        patch.object(launcher, "AGENT", tmp_path),
        patch.object(launcher, "prompt", side_effect=["https://remote.test", "admin", "site"]),
        patch.object(launcher.getpass, "getpass", return_value="confidential-password"),
        patch.object(
            launcher,
            "api_post",
            side_effect=[
                {"access_token": "temporary-token"},
                {"credential": "12345678-1234-1234-1234-123456789abc.secret"},
            ],
        ),
    ):
        launcher.setup_agent(False)
    config = (tmp_path / ".env").read_text()
    assert "confidential-password" not in config
    assert "temporary-token" not in config


def test_launcher_modes_start_correct_services():
    for mode, expected in (
        ("dashboard", [launcher.ROOT]),
        ("agent", [launcher.AGENT]),
        ("both", [launcher.ROOT, launcher.AGENT]),
    ):
        commands = []

        def fake_run(command, **_kwargs):
            output = "linux" if command[1] == "info" else ""
            return SimpleNamespace(stdout=output)

        def fake_compose(directory, *args, _commands=commands, **_kwargs):
            _commands.append((directory, args))
            return SimpleNamespace(stdout="")

        with (
            patch.object(launcher.sys, "argv", ["start.py", "--mode", mode]),
            patch.object(launcher, "run", side_effect=fake_run),
            patch.object(launcher, "compose", side_effect=fake_compose),
            patch.object(launcher, "setup_dashboard") as dashboard,
            patch.object(launcher, "setup_agent") as agent,
            patch.object(launcher, "verify_agent") as verify,
            patch.object(launcher.platform, "system", return_value="Linux"),
        ):
            launcher.main()
            assert [item[0] for item in commands] == expected
            assert dashboard.called == (mode != "agent")
            assert agent.called == (mode != "dashboard")
            assert verify.called == (mode != "dashboard")


def test_verify_agent_rejects_later_connection_failure():
    def fake_compose(_directory, command, *args, **kwargs):
        if command == "ps":
            return SimpleNamespace(stdout="container-id")
        return SimpleNamespace(
            stdout="INFO Connected to the control center\nERROR Control center returned HTTP 401"
        )

    with (
        patch.object(launcher, "compose", side_effect=fake_compose),
        patch.object(launcher.time, "monotonic", side_effect=[0, 0, 2]),
        patch.object(launcher.time, "sleep"),
    ):
        with pytest.raises(RuntimeError, match="did not confirm"):
            launcher.verify_agent("2026-01-01T00:00:00Z", timeout=1)
