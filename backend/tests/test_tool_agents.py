import csv
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_agent_mtr import agent


def test_dns_query_reports_response_status_and_output():
    job = {"target": "example.com", "server": "8.8.8.8", "record_type": "A"}
    answer = (
        ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 123\n"
        ";; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1\n"
        ";; ANSWER SECTION:\nexample.com. 300 IN A 192.0.2.1\n"
    )
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, answer, "")
    ) as run:
        result = agent.run_dns(job)
        assert result["success"]
        assert result["report"]["status"] == "NOERROR"
        assert result["report"]["answer_count"] == 1
        assert "192.0.2.1" in result["report"]["output"]
        assert run.call_args.args[0] == [
            "dig", "-r", "@8.8.8.8", "-q", "example.com", "-t", "A",
            "+time=3", "+tries=1", "+noall", "+comments", "+answer", "+stats",
        ]
        assert run.call_args.kwargs["timeout"] == 15
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, answer.replace("NOERROR", "NXDOMAIN"), ""),
    ):
        result = agent.run_dns(job)
        assert not result["success"] and result["report"]["status"] == "NXDOMAIN"
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, answer.replace("NOERROR", "SERVFAIL"), ""),
    ):
        assert not agent.run_dns(job)["success"]
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(
            [], 0, answer.replace("ANSWER: 1", "ANSWER: 0").split(";; ANSWER SECTION:")[0], ""
        ),
    ):
        result = agent.run_dns({**job, "target": "_dmarc.example.com", "record_type": "TXT"})
        assert result["success"] and result["report"]["answer_count"] == 0
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "bad output", "")
    ):
        assert not agent.run_dns(job)["success"]
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, answer.split(";; flags:")[0], ""),
    ):
        assert agent.run_dns(job)["error"] == "DNS response missing answer count"
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 9, "no servers", "")
    ):
        result = agent.run_dns(job)
        assert not result["success"] and result["report"]["output"] == "no servers"
    with patch.object(agent.subprocess, "run", side_effect=subprocess.TimeoutExpired("dig", 15)):
        assert not agent.run_dns(job)["success"]
    with patch.object(agent.subprocess, "run", side_effect=OSError("dig missing")):
        assert "dig missing" in agent.run_dns(job)["error"]
    for bad in (
        {**job, "server": "example.com"},
        {**job, "server": "fe80::1%eth0"},
        {**job, "target": "-bad"},
        {**job, "target": "::1"},
        {**job, "target": "example.com;id"},
        {**job, "record_type": "ANY"},
    ):
        assert not agent.run_dns(bad)["success"]


def test_iperf_success_and_errors():
    job = {"target": "example.com", "port": 5201, "duration": 3}
    report = {"end": {"sum_received": {"bits_per_second": 42}}}
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 0, json.dumps(report), ""),
    ) as run:
        assert agent.run_iperf(job) == {"success": True, "report": report}
        assert run.call_args.args[0][:3] == ["iperf3", "--client", "example.com"]
        assert run.call_args.kwargs["timeout"] == 90
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 1, '{"error":"refused"}', ""),
    ):
        assert agent.run_iperf(job)["error"] == "refused"
    assert not agent.run_iperf({**job, "target": "-bad"})["success"]


def test_sipp_statistics_success_and_failed_calls():
    job = {
        "target": "example.com",
        "port": 5060,
        "calls": 2,
        "rate": 1,
        "concurrency": 2,
        "service": "1000",
    }

    def run(args, **kwargs):
        assert args[1] == "example.com:5060"
        assert "-sn" in args and "uac" in args
        path = Path(args[args.index("-stf") + 1])
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["SuccessfulCall(C)", "FailedCall(C)"], delimiter=";"
            )
            writer.writeheader()
            writer.writerow({"SuccessfulCall(C)": 2, "FailedCall(C)": 0})
        return subprocess.CompletedProcess(args, 0, "", "")

    with patch.object(agent.subprocess, "run", side_effect=run):
        result = agent.run_sipp(job)
        assert result["success"]
        assert result["report"]["successful_calls"] == 2
        failure = agent.run_sipp({**job, "calls": 3})
        assert not failure["success"]
        assert failure["report"]["successful_calls"] == 2
    assert not agent.run_sipp({**job, "service": "bad;command"})["success"]


def test_iperf_receiver_signals_readiness_and_cleans_up():
    process = MagicMock()
    process.pid = 123
    process.returncode = 0
    process.poll.side_effect = [None, 0]
    context = MagicMock()
    context.__enter__.return_value = process

    def launch(args, **kwargs):
        assert args == ["iperf3", "--server", "--one-off", "--port", "5201", "--json"]
        kwargs["stdout"].write(json.dumps({"end": {"sum_received": {"bits_per_second": 10}}}))
        kwargs["stdout"].flush()
        return context

    with (
        patch.object(agent.subprocess, "Popen", side_effect=launch),
        patch.object(agent, "listener_ready", return_value=True),
        patch.object(agent, "post") as ready,
    ):
        result = agent.run_iperf_server({"id": "test", "port": 5201}, "https://api", "secret")
    assert result["success"]
    ready.assert_called_once_with("https://api", "secret", "/api/v1/agent/jobs/test/ready", {})
    process.wait.assert_called_once_with(timeout=115)


def test_nmap_tcp_scan_and_incomplete_output():
    job = {"target": "127.0.0.1", "ports": [22, 443, 8080]}
    xml = """<nmaprun><host><status state="up"/><address addr="127.0.0.1"/>
    <ports><extraports state="closed" count="2"/><port protocol="tcp" portid="443">
    <state state="open"/><service name="https"/></port></ports></host></nmaprun>"""
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, xml, "")
    ) as run:
        result = agent.run_nmap(job)
        assert result["report"]["ports"] == [
            {"port": 443, "protocol": "tcp", "state": "open", "service": "https"}
        ]
        assert result["report"]["other_ports"] == [{"state": "closed", "count": 2}]
        assert run.call_args.args[0] == [
            "nmap",
            "-sT",
            "-Pn",
            "-n",
            "--max-retries",
            "1",
            "--host-timeout",
            "80s",
            "-p",
            "22,443,8080",
            "-oX",
            "-",
            "127.0.0.1",
        ]
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, xml, "")
    ):
        assert not agent.run_nmap({**job, "ports": [22]})["success"]
    for ports in ([], [22, 22], [True], [65536], list(range(1, 102))):
        assert not agent.run_nmap({**job, "ports": ports})["success"]
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "<nmaprun/>", "")
    ):
        assert not agent.run_nmap(job)["success"]
    with patch.object(agent.subprocess, "run", side_effect=subprocess.TimeoutExpired("nmap", 90)):
        assert not agent.run_nmap(job)["success"]


def test_ping_and_traceroute_results_and_failures():
    with patch.object(
        agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "output", "")
    ) as run:
        assert agent.run_ping({"target": "::1", "count": 4}) == {
            "success": True,
            "report": {"output": "output"},
        }
        assert "-6" in run.call_args.args[0]
        assert agent.run_traceroute({"target": "example.com", "max_hops": 12})["success"]
        assert run.call_args.args[0][:3] == ["traceroute", "-n", "-q"]
        assert run.call_args.args[0][7] == "12"
    with patch.object(
        agent.subprocess,
        "run",
        return_value=subprocess.CompletedProcess([], 1, "100% packet loss", ""),
    ):
        result = agent.run_ping({"target": "example.com", "count": 4})
        assert not result["success"] and result["report"]["output"] == "100% packet loss"
    assert not agent.run_ping({"target": "-bad", "count": 4})["success"]
    assert not agent.run_ping({"target": "localhost", "count": 11})["success"]
    assert not agent.run_traceroute({"target": "192.0.2.0/24", "max_hops": 30})["success"]
    for max_hops in (0, 31, True):
        assert not agent.run_traceroute({"target": "localhost", "max_hops": max_hops})["success"]
    with patch.object(agent.subprocess, "run", side_effect=OSError("missing executable")):
        result = agent.run_traceroute({"target": "localhost", "max_hops": 30})
        assert "missing executable" in result["error"]
