"""Exercise the packaged tools against loopback; intended for CI."""

import os
import socket
import struct
import subprocess
import threading
import time
from unittest.mock import patch

import brgrbyte_agent as agent

assert os.geteuid() != 0
subprocess.run(["dig", "-v"], capture_output=True, text=True, check=True)
for package in ("nmap", "nmap-common"):
    version = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", package],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert version == "7.95+dfsg-3", (package, version)
mtr = agent.run_mtr({"engine": "mtr", "target": "127.0.0.1", "cycles": 1})
assert mtr["success"], mtr
hops = mtr["report"]["report"]["hubs"]
assert any(hop["host"] == "127.0.0.1" and float(hop["Loss%"]) < 100 for hop in hops), mtr

ping = agent.run_ping({"target": "127.0.0.1", "count": 1})
assert ping["success"] and "1 received" in ping["report"]["output"], ping
trace = agent.run_traceroute({"target": "127.0.0.1"})
assert trace["success"] and "127.0.0.1" in trace["report"]["output"], trace

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dns_socket:
    dns_socket.bind(("127.0.0.1", 0))
    dns_socket.settimeout(10)
    dns_port = dns_socket.getsockname()[1]

    def respond_to_dns():
        query, peer = dns_socket.recvfrom(4096)
        end = 12
        while query[end]:
            end += 1 + query[end]
        end += 5
        header = query[:2] + struct.pack("!HHHHH", 0x8180, 1, 1, 0, 0)
        answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton("192.0.2.1")
        dns_socket.sendto(header + query[12:end] + answer, peer)

    responder = threading.Thread(target=respond_to_dns)
    responder.start()
    real_run = subprocess.run

    def run_on_test_port(args, **kwargs):
        return real_run([*args[:2], "-p", str(dns_port), *args[2:]], **kwargs)

    try:
        with patch.object(agent.subprocess, "run", side_effect=run_on_test_port):
            dns = agent.run_dns(
                {"target": "example.test", "server": "127.0.0.1", "record_type": "A"}
            )
        assert dns["success"] and dns["report"]["answer_count"] == 1, dns
        assert "192.0.2.1" in dns["report"]["output"], dns
    finally:
        responder.join(timeout=11)

with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    scan = agent.run_nmap({"target": "127.0.0.1", "ports": [port]})
    assert scan["success"], scan
    assert any(
        item["port"] == port and item["state"] == "open" for item in scan["report"]["ports"]
    ), scan


def receiver_ready(_base, _credential, _path, _data):
    result = agent.run_iperf({"target": "127.0.0.1", "port": 15201, "duration": 1})
    if not result["success"]:
        raise RuntimeError(f"iPerf3 client failed: {result}")
    return {}


agent.post = receiver_ready
receiver = agent.run_iperf_server({"id": "smoke", "port": 15201}, "", "")
assert receiver["success"], receiver

server = subprocess.Popen(
    ["sipp", "-sn", "uas", "-i", "127.0.0.1", "-p", "15060", "-m", "1", "-nostdin"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    time.sleep(1)
    assert server.poll() is None, "SIPp UAS exited before the test"
    result = agent.run_sipp(
        {
            "target": "127.0.0.1",
            "port": 15060,
            "service": "service",
            "calls": 1,
            "rate": 1,
            "concurrency": 1,
        }
    )
    assert result["success"], result
finally:
    if server.poll() is None:
        server.terminate()
        server.wait(timeout=10)
