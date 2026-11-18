"""Exercise the packaged tools against loopback; intended for CI."""

import os
import socket
import subprocess
import time

import networkpath_agent as agent

assert os.geteuid() != 0
mtr = agent.run_mtr({"engine": "mtr", "target": "127.0.0.1", "cycles": 1})
assert mtr["success"], mtr
hops = mtr["report"]["report"]["hubs"]
assert any(hop["host"] == "127.0.0.1" and float(hop["Loss%"]) < 100 for hop in hops), mtr

ping = agent.run_ping({"target": "127.0.0.1", "count": 1})
assert ping["success"] and "1 received" in ping["report"]["output"], ping
trace = agent.run_traceroute({"target": "127.0.0.1"})
assert trace["success"] and "127.0.0.1" in trace["report"]["output"], trace
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
