# Architecture

## Components and trust boundaries

```mermaid
flowchart LR
  Browser -->|HTTPS in production / HTTP local| API[FastAPI control plane]
  API --> DB[(PostgreSQL)]
  AgentA[Source agent] <-->|Authenticated outbound management WebSocket| API
  AgentB[Destination agent] <-->|Authenticated outbound management WebSocket| API
  AgentA ==>|Direct test traffic; separate data plane| AgentB
```

The browser uses a JWT-authenticated REST API. The control center owns inventory, coordination, and result persistence. Agents are intended to initiate authenticated outbound management connections; agent-to-agent test packets must not be proxied through the control center. Agent transport and test execution are not implemented in the foundation release.

## Test orchestration target

```mermaid
sequenceDiagram
  actor Engineer
  participant API as Control center
  participant DB as PostgreSQL
  participant Dest as Destination agent
  participant Src as Source agent
  Engineer->>API: Create test request
  API->>DB: Persist CREATED session
  API->>Dest: Prepare receiver (management channel)
  Dest-->>API: READY / preparation error
  API->>Src: Execute test against destination directly
  Src-->>API: Progress and source measurements
  Dest-->>API: Receiver measurements (where applicable)
  API->>DB: Persist terminal state and results
  API-->>Engineer: Completion update
```

Persisted test states are constrained to `CREATED`, `PREPARING`, `READY`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, and `TIMEOUT`. Dispatch success alone must never mean a test succeeded.

## Agent registration target

```mermaid
sequenceDiagram
  participant Agent
  participant API as Control center
  participant DB as PostgreSQL
  Agent->>API: Authenticated registration request
  API->>DB: Validate unique credential and record inventory
  API-->>Agent: Agent identity and rotated credential
  Agent->>API: Outbound authenticated WebSocket
  API-->>Agent: Heartbeat acknowledgement / test instruction
```

Registration, credential issuance/rotation, WebSockets, and heartbeat processing are future work. The initial schema defines inventory fields but does not yet provision agent credentials.
