"""brgrByte site agent. Configuration is supplied through environment variables."""

import csv
import ipaddress
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

LOG = logging.getLogger("brgrbyte-agent")


def valid_target(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return bool(
            re.fullmatch(
                r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?",
                target,
            )
        )


def run_mtr(job: dict) -> dict:
    target, cycles = job.get("target"), job.get("cycles")
    if (
        job.get("engine") != "mtr"
        or not isinstance(target, str)
        or not valid_target(target)
        or type(cycles) is not int
        or not 1 <= cycles <= 20
    ):
        return {"success": False, "error": "Invalid MTR job"}
    try:
        completed = subprocess.run(
            [
                "mtr",
                "--json",
                "--report",
                "-n",
                "--report-cycles",
                str(cycles),
                "--max-ttl",
                "30",
                target,
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": str(exc)[:1000]}
    if completed.returncode != 0:
        return {
            "success": False,
            "error": (completed.stderr.strip() or f"MTR exited with {completed.returncode}")[:1000],
        }
    try:
        report = json.loads(completed.stdout)
        if not isinstance(report, dict) or not isinstance(
            report.get("report", {}).get("hubs"), list
        ):
            raise ValueError("MTR output does not contain a hop list")
    except (ValueError, AttributeError) as exc:
        stderr = completed.stderr.strip() or "<empty>"
        stdout = completed.stdout[:300] or "<empty>"
        return {
            "success": False,
            "error": (
                f"Invalid MTR JSON output (exit code {completed.returncode}): {exc}; "
                f"stderr: {stderr[:300]}; stdout: {stdout!r}"
            )[:1000],
        }
    return {"success": True, "report": report}


def valid_integer(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def ipv6_option(target: str) -> list[str]:
    try:
        return ["-6"] if ipaddress.ip_address(target).version == 6 else []
    except ValueError:
        return []


def run_nmap(job: dict) -> dict:
    target, ports = job.get("target"), job.get("ports")
    if (
        not isinstance(target, str)
        or not valid_target(target)
        or not isinstance(ports, list)
        or not 1 <= len(ports) <= 100
        or any(not valid_integer(port, 1, 65535) for port in ports)
        or len(set(ports)) != len(ports)
    ):
        return {"success": False, "error": "Invalid Nmap job"}
    try:
        completed = subprocess.run(
            [
                "nmap",
                "-sT",
                "-Pn",
                "-n",
                "--max-retries",
                "1",
                "--host-timeout",
                "80s",
                *ipv6_option(target),
                "-p",
                ",".join(map(str, ports)),
                "-oX",
                "-",
                target,
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "success": False,
                "error": (completed.stderr.strip() or f"Nmap exited with {completed.returncode}")[
                    :1000
                ],
            }
        root = ET.fromstring(completed.stdout)
        hosts = root.findall("host")
        if root.tag != "nmaprun" or len(hosts) != 1:
            raise ValueError("Nmap did not return one complete host report")
        host = hosts[0]
        if host.find("status") is None or host.find("status").get("state") != "up":
            raise ValueError("Nmap did not complete the host scan")
        port_list = []
        for item in host.findall("./ports/port"):
            state = item.find("state")
            service = item.find("service")
            port_list.append(
                {
                    "port": int(item.attrib["portid"]),
                    "protocol": item.attrib["protocol"],
                    "state": state.attrib["state"],
                    "service": service.get("name") if service is not None else None,
                }
            )
        summary = [
            {"state": item.attrib["state"], "count": int(item.attrib["count"])}
            for item in host.findall("./ports/extraports")
        ]
        if len(port_list) + sum(item["count"] for item in summary) != len(ports):
            raise ValueError("Nmap returned an incomplete port report")
        addresses = [item.attrib["addr"] for item in host.findall("address")]
        return {
            "success": True,
            "report": {
                "addresses": addresses,
                "ports": port_list,
                "other_ports": summary,
            },
        }
    except (
        OSError,
        subprocess.TimeoutExpired,
        ET.ParseError,
        ValueError,
        KeyError,
        AttributeError,
    ) as exc:
        return {"success": False, "error": f"Nmap failed: {exc}"[:1000]}


def run_ping(job: dict) -> dict:
    target, count = job.get("target"), job.get("count")
    if not isinstance(target, str) or not valid_target(target) or not valid_integer(count, 1, 10):
        return {"success": False, "error": "Invalid ping job"}
    return run_text_probe(
        ["ping", "-n", "-c", str(count), "-W", "2", "-w", "30", *ipv6_option(target), target],
        "Ping",
    )


def run_traceroute(job: dict) -> dict:
    target, max_hops = job.get("target"), job.get("max_hops", 30)
    if (
        not isinstance(target, str)
        or not valid_target(target)
        or not valid_integer(max_hops, 1, 30)
    ):
        return {"success": False, "error": "Invalid traceroute job"}
    return run_text_probe(
        [
            "traceroute",
            "-n",
            "-q",
            "1",
            "-w",
            "2",
            "-m",
            str(max_hops),
            *ipv6_option(target),
            target,
        ],
        "Traceroute",
    )


def run_dns(job: dict) -> dict:
    target, server, record_type = (job.get(key) for key in ("target", "server", "record_type"))
    if (
        not isinstance(target, str)
        or not re.fullmatch(
            r"(?=.{1,253}\Z)(?:[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?\.)*"
            r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?\.?",
            target,
        )
        or not isinstance(server, str)
    ):
        return {"success": False, "error": "Invalid DNS job"}
    try:
        address = ipaddress.ip_address(server)
        if getattr(address, "scope_id", None):
            raise ValueError("Scoped IPv6 addresses are not supported")
    except ValueError:
        return {"success": False, "error": "Invalid DNS server address"}
    if record_type not in ("A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT"):
        return {"success": False, "error": "Invalid DNS record type"}
    try:
        completed = subprocess.run(
            [
                "dig", "-r", f"@{address}", "-q", target, "-t", record_type,
                "+time=3", "+tries=1", "+noall", "+comments", "+answer", "+stats",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": f"DNS query failed: {exc}"[:1000]}
    report = {"server": str(address), "record_type": record_type, "output": completed.stdout}
    if completed.returncode != 0:
        return {
            "success": False,
            "error": (
                completed.stderr.strip() or f"DNS query exited {completed.returncode}"
            )[:1000],
            "report": report,
        }
    match = re.search(r"^;; ->>HEADER<<- .* status: ([A-Z0-9]+),", completed.stdout, re.MULTILINE)
    if not match:
        return {"success": False, "error": "DNS response missing status", "report": report}
    report["status"] = match.group(1)
    if report["status"] != "NOERROR":
        return {"success": False, "error": f"DNS response: {report['status']}", "report": report}
    answer_count = re.search(
        r"^;; flags:.*;\s*QUERY: \d+, ANSWER: (\d+),", completed.stdout, re.MULTILINE
    )
    if not answer_count:
        return {"success": False, "error": "DNS response missing answer count", "report": report}
    report["answer_count"] = int(answer_count.group(1))
    return {"success": True, "report": report}


def run_text_probe(args: list[str], name: str) -> dict:
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": f"{name} failed: {exc}"[:1000]}
    report = {"output": completed.stdout} if completed.stdout.strip() else None
    if completed.returncode != 0:
        result = {
            "success": False,
            "error": (completed.stderr.strip() or f"{name} exited with {completed.returncode}")[
                :1000
            ],
        }
        if report is not None:
            result["report"] = report
        return result
    if report is None:
        return {"success": False, "error": f"{name} returned no output"}
    return {"success": True, "report": report}


def run_iperf(job: dict) -> dict:
    target, port, duration = job.get("target"), job.get("port"), job.get("duration")
    if (
        not isinstance(target, str)
        or not valid_target(target)
        or not valid_integer(port, 1024, 65535)
        or not valid_integer(duration, 1, 60)
    ):
        return {"success": False, "error": "Invalid iPerf3 job"}
    try:
        completed = subprocess.run(
            ["iperf3", "--client", target, "--port", str(port), "--time", str(duration), "--json"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": str(exc)[:1000]}
    if completed.returncode != 0 and not completed.stdout.strip():
        return {
            "success": False,
            "error": (completed.stderr.strip() or f"iPerf3 exited {completed.returncode}")[:1000],
        }
    try:
        report = json.loads(completed.stdout)
        if not isinstance(report, dict):
            raise ValueError("iPerf3 output is not an object")
        if completed.returncode != 0 or report.get("error"):
            error = report.get("error") or completed.stderr.strip()
            return {"success": False, "error": str(error or "iPerf3 failed")[:1000]}
        if not isinstance(report.get("end"), dict) or not report["end"].get("sum_received"):
            raise ValueError("iPerf3 output has no receiver measurements")
    except ValueError as exc:
        return {"success": False, "error": f"Invalid iPerf3 output: {exc}"[:1000]}
    return {"success": True, "report": report}


def run_sipp(job: dict) -> dict:
    target = job.get("target")
    port, calls, rate, concurrency = (job.get(k) for k in ("port", "calls", "rate", "concurrency"))
    service = job.get("service")
    if (
        not isinstance(target, str)
        or not valid_target(target)
        or not isinstance(service, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", service)
        or not valid_integer(port, 1, 65535)
        or not valid_integer(calls, 1, 1000)
        or not valid_integer(rate, 1, 20)
        or not valid_integer(concurrency, 1, 100)
    ):
        return {"success": False, "error": "Invalid SIPp job"}
    endpoint = f"[{target}]:{port}" if ":" in target else f"{target}:{port}"
    with tempfile.TemporaryDirectory(prefix="brgrbyte-sipp-") as directory:
        stats = os.path.join(directory, "statistics.csv")
        try:
            completed = subprocess.run(
                [
                    "sipp",
                    endpoint,
                    "-sn",
                    "uac",
                    "-t",
                    "u1",
                    "-s",
                    service,
                    "-m",
                    str(calls),
                    "-r",
                    str(rate),
                    "-l",
                    str(concurrency),
                    "-timeout",
                    "80s",
                    "-timeout_error",
                    "-nostdin",
                    "-trace_stat",
                    "-stat_delimiter",
                    ";",
                    "-stf",
                    stats,
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if not os.path.exists(stats):
                raise ValueError(
                    (
                        completed.stderr.strip()
                        or f"SIPp exited {completed.returncode} without stats"
                    )[:800]
                )
            with open(stats, encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            if not rows:
                raise ValueError("SIPp statistics are empty")
            counters = rows[-1]
            successful = int(counters["SuccessfulCall(C)"])
            failed = int(counters["FailedCall(C)"])
            report = {
                "successful_calls": successful,
                "failed_calls": failed,
                "statistics": counters,
            }
            if completed.returncode != 0 or failed != 0 or successful != calls:
                return {
                    "success": False,
                    "error": (
                        f"SIPp exited {completed.returncode}; "
                        f"{successful}/{calls} calls succeeded, {failed} failed"
                    ),
                    "report": report,
                }
            return {"success": True, "report": report}
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            return {"success": False, "error": f"SIPp failed: {exc}"[:1000]}


def listener_ready(pid: int, port: int) -> bool:
    sockets = set()
    for fd in os.listdir(f"/proc/{pid}/fd"):
        try:
            sockets.add(os.readlink(f"/proc/{pid}/fd/{fd}"))
        except FileNotFoundError:
            continue
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        with open(path, encoding="ascii") as stream:
            for line in stream:
                fields = line.split()
                if (
                    len(fields) > 9
                    and fields[3] == "0A"
                    and fields[1].split(":")[-1] == f"{port:04X}"
                    and f"socket:[{fields[9]}]" in sockets
                ):
                    return True
    return False


def run_iperf_server(job: dict, base_url: str, credential: str) -> dict:
    port = job.get("port")
    if not valid_integer(port, 1024, 65535):
        return {"success": False, "error": "Invalid iPerf3 receiver port"}
    try:
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as output:
            with subprocess.Popen(
                ["iperf3", "--server", "--one-off", "--port", str(port), "--json"],
                stdout=output,
                stderr=subprocess.STDOUT,
            ) as process:
                try:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError("iPerf3 receiver exited before listening")
                        if listener_ready(process.pid, port):
                            break
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("iPerf3 receiver did not begin listening")
                    post(base_url, credential, f"/api/v1/agent/jobs/{job['id']}/ready", {})
                    process.wait(timeout=115)
                    output.seek(0)
                    report = json.load(output)
                    if process.returncode != 0 or report.get("error") or not report.get("end"):
                        raise RuntimeError(str(report.get("error") or "iPerf3 receiver failed"))
                    return {"success": True, "report": report}
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.TimeoutExpired,
        urllib.error.URLError,
    ) as exc:
        return {"success": False, "error": f"iPerf3 receiver failed: {exc}"[:1000]}


def post(base_url: str, credential: str, path: str, data: dict) -> dict:
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {credential}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read()
        return json.loads(content) if content else {}


def environment_setting(name: str, legacy_name: str) -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return os.environ[legacy_name]
    except KeyError as exc:
        raise RuntimeError(f"Missing required setting: {name}") from exc


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    base_url = environment_setting("BRGRBYTE_URL", "NETWORKPATH_URL")
    credential = environment_setting("BRGRBYTE_AGENT_CREDENTIAL", "NETWORKPATH_AGENT_CREDENTIAL")
    base_url = base_url.rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError("BRGRBYTE_URL must use HTTPS except on localhost")
    pending = None
    last_connection_log = 0.0
    while True:
        try:
            if pending is not None:
                post(base_url, credential, f"/api/v1/agent/jobs/{pending[0]}/result", pending[1])
                LOG.info("Submitted result for job %s", pending[0])
                pending = None
            response = post(
                base_url,
                credential,
                "/api/v1/agent/poll",
                {
                    "hostname": socket.gethostname(),
                    "os_name": platform.system(),
                    "architecture": platform.machine(),
                    "mtr_available": shutil.which("mtr") is not None,
                    "available_engines": [
                        engine
                        for engine, executable in (
                            ("mtr", "mtr"),
                            ("iperf3", "iperf3"),
                            ("sipp", "sipp"),
                            ("nmap", "nmap"),
                            ("ping", "ping"),
                            ("traceroute", "traceroute"),
                            ("dns", "dig"),
                        )
                        if shutil.which(executable) is not None
                    ],
                },
            )
            if time.monotonic() - last_connection_log >= 30:
                LOG.info("Connected to the control center")
                last_connection_log = time.monotonic()
            job = response.get("job")
            if job:
                LOG.info("Running job %s", job["id"])
                if job["engine"] == "mtr":
                    result = run_mtr(job)
                elif job["engine"] == "iperf3":
                    result = run_iperf(job)
                elif job["engine"] == "iperf3-server":
                    result = run_iperf_server(job, base_url, credential)
                elif job["engine"] == "sipp":
                    result = run_sipp(job)
                elif job["engine"] == "nmap":
                    result = run_nmap(job)
                elif job["engine"] == "ping":
                    result = run_ping(job)
                elif job["engine"] == "traceroute":
                    result = run_traceroute(job)
                elif job["engine"] == "dns":
                    result = run_dns(job)
                else:
                    result = {"success": False, "error": "Unsupported engine"}
                pending = (job["id"], result)
                continue
        except urllib.error.HTTPError as exc:
            if pending is not None and exc.code == 409:
                LOG.error(
                    "Result for job %s was rejected as expired or already submitted", pending[0]
                )
                pending = None
            else:
                LOG.error("Control center returned HTTP %s", exc.code)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            LOG.error("Agent communication failed: %s", exc)
        time.sleep(5)


if __name__ == "__main__":
    main()
