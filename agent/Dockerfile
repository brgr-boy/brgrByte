FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends mtr-tiny iperf3 sip-tester nmap iputils-ping traceroute ca-certificates \
    && chmod 4755 /usr/bin/mtr-packet \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin networkpath \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --chown=10001:10001 networkpath_agent.py container_smoke.py ./
USER 10001:10001

CMD ["python", "/app/networkpath_agent.py"]
