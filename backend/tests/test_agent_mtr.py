import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "brgrbyte_agent", Path(__file__).resolve().parents[2] / "agent" / "brgrbyte_agent.py"
)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

def test_agent_settings_support_current_and_previous_names(monkeypatch):
    monkeypatch.setenv("BRGRBYTE_URL", "https://current.example")
    monkeypatch.setenv("NETWORKPATH_URL", "https://previous.example")
    assert agent.environment_setting("BRGRBYTE_URL", "NETWORKPATH_URL") == "https://current.example"

    monkeypatch.delenv("BRGRBYTE_URL")
    assert agent.environment_setting("BRGRBYTE_URL", "NETWORKPATH_URL") == "https://previous.example"


def test_mtr_uses_fixed_arguments_and_parses_report():
    job = {"engine": "mtr", "target": "example.com", "cycles": 5}
    process = subprocess.CompletedProcess([], 0, '{"report":{"hubs":[{"host":"192.0.2.1"}]}}', "")
    with patch.object(agent.subprocess, "run", return_value=process) as run:
        result = agent.run_mtr(job)
    assert result["success"]
    assert run.call_args.args[0][:4] == ["mtr", "--json", "--report", "-n"]
    assert run.call_args.args[0][-1] == "example.com"
    assert run.call_args.kwargs["timeout"] == 90
    assert "shell" not in run.call_args.kwargs


def test_mtr_rejects_bad_jobs_and_bad_output():
    assert not agent.run_mtr({"engine": "mtr", "target": "-help", "cycles": 1})["success"]
    assert not agent.run_mtr({"engine": "mtr", "target": "example.com", "cycles": 21})["success"]
    process = subprocess.CompletedProcess([], 0, "not json", "mtr-packet permission denied")
    with patch.object(agent.subprocess, "run", return_value=process):
        result = agent.run_mtr({"engine": "mtr", "target": "::1", "cycles": 1})
    assert not result["success"]
    assert "mtr-packet permission denied" in result["error"]
    assert "stdout: 'not json'" in result["error"]
    assert "exit code 0" in result["error"]


def test_mtr_reports_process_errors_and_timeouts():
    job = {"engine": "mtr", "target": "example.com", "cycles": 1}
    process = subprocess.CompletedProcess([], 1, "", "permission denied")
    with patch.object(agent.subprocess, "run", return_value=process):
        assert agent.run_mtr(job) == {"success": False, "error": "permission denied"}
    with patch.object(agent.subprocess, "run", side_effect=subprocess.TimeoutExpired("mtr", 90)):
        assert not agent.run_mtr(job)["success"]
