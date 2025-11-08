Oczywiście. Oto w pełni profesjonalny plik `README.md` dla Twojego nowego pakietu `domain-ops`.
# AstraDesk Domain Pack: Operations (SRE/DevOps)

[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](../../LICENSE)

<br>

## 1. Overview

The **Operations Domain Pack** is a specialized, pluggable module for the AstraDesk framework, designed to empower SRE and DevOps teams. It provides a set of agents and tools focused on automating operational tasks, interacting with infrastructure, and enforcing runbook procedures.

This pack follows an **action-oriented** philosophy. Its primary goal is to reliably execute specific, well-defined tasks rather than generating conversational answers.

### Key Features

- **`OpsAgent`**: An agent optimized for operational workflows. It prioritizes tool execution and provides clear, deterministic error reporting without falling back to RAG.

- **Kubernetes Integration**: Includes a production-ready `restart_service` tool that interacts directly with the Kubernetes API to perform controlled rollout restarts of deployments.

- **RBAC Enforcement**: All sensitive actions are protected by Role-Based Access Control, leveraging policies defined in the core `runtime` module.

- **Extensible**: Designed to be easily extended with new tools for interacting with other infrastructure components like Prometheus, Ansible, or cloud provider APIs.

<br>

## 2. Integration with AstraDesk

This pack is designed to be seamlessly integrated into the AstraDesk Enterprise AI Agents Framework.

- **Workspace**: It is a member of the `uv` workspace defined in the root `pyproject.toml`, allowing for unified dependency management and testing.

- **Dynamic Loading**: The `OpsAgent` and its tools are discovered and registered at runtime by the `ToolRegistry` in the `api-gateway` service.

- **Core Dependencies**: It relies on `astradesk-core` for shared exceptions and `astradesk-api-gateway` for base classes and runtime components.

<br>

## 3. Components

### Agents

- **`agents/ops.py`**: Contains the `OpsAgent` class. Its core strategy is to execute plans from the `KeywordPlanner` or `LLMPlanner`. If a tool fails or is not found, it reports the error directly and does not attempt to query the RAG knowledge base.

### Tools

- **`tools/actions.py`**:
  - `restart_service(service: str)`: A tool that connects to the Kubernetes API to trigger a rollout restart for a specified deployment. It is protected by RBAC (requires the `sre` role) and validates the target service against a configurable allowlist.

<br>

## 4. Local Development and Testing

All commands should be run from the **root of the AstraDesk Enterprise AI Agents Framework**.

### Running Tests

To run the unit tests specific to this pack, you can use `pytest` with a specific path:

```bash
# Ensure you are in the root `astradesk/` directory
uv run pytest packages/domain-ops/tests/
```

Alternatively, running the global test command will also include tests from this pack:

```bash
make test
```

### Dependencies

- **Production dependencies** are defined in `pyproject.toml` and include `kubernetes-asyncio`.

- **Development dependencies** are also in `pyproject.toml` and include `pytest` and `pytest-asyncio`.

To install all dependencies for the entire workspace, run `uv sync` from the root directory.

<br>

## 5. Configuration

The tools within this pack rely on environment variables for configuration:

- `KUBERNETES_NAMESPACE`: The Kubernetes namespace where the target services are deployed (defaults to `default`).
- `ALLOWED_SERVICES`: A comma-separated string of deployment names that are permitted to be restarted (defined within `tools/actions.py`).
- `REQUIRED_ROLE_RESTART`: The role claim required in the JWT to execute the `restart_service` tool (defaults to `sre`).

These variables should be set in the `.env` file at the root of the project.

---

_This document is part of the AstraDesk framework._
