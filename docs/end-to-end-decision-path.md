# End-to-End Decision Path Documentation

**Goal: Make it legible to security reviewers**

This document provides a comprehensive overview of the Provability Fabric Testbed's end-to-end decision path, from observation to safety case generation. It includes explicit SLO thresholds, security statements, and examples for security reviewers.

## Table of Contents

1. [System Overview](#system-overview)
2. [End-to-End Decision Path](#end-to-end-decision-path)
3. [Security Architecture](#security-architecture)
4. [SLO Thresholds](#slo-thresholds)
5. [Non-Interference Statement](#non-interference-statement)
6. [Certificate Examples](#certificate-examples)
7. [Security Review Checklist](#security-review-checklist)

## System Overview

The Provability Fabric Testbed is a comprehensive testing and validation platform that implements provable security guarantees through cryptographic proofs, attestation, and audit trails. The system processes requests through multiple stages, each with specific security controls and performance guarantees.

### Key Components

- **Ingress Layer**: Request validation and rate limiting
- **Gateway**: Request routing and authentication
- **Kernel**: Decision engine with cryptographic verification
- **Tool Broker**: Secure tool execution and sandboxing
- **Egress**: Output validation and certificate generation
- **Safety Case Generator**: Comprehensive audit trail creation

## End-to-End Decision Path

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│ Observation │───▶│   Retrieve   │───▶│    Plan     │───▶│   Kernel    │
│             │    │  (Receipt)   │    │   (DSL)     │    │             │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                                                              │
                                                              ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│ Safety Case │◀───│    Egress    │◀───│ Tool Broker │◀───│  Decision   │
│             │    │   (Cert)     │    │             │    │             │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

### Stage 1: Observation
- **Input**: Raw request data from external sources
- **Security Controls**: Input sanitization, size limits, format validation
- **Output**: Validated observation object
- **Performance Target**: < 100ms processing time

### Stage 2: Retrieve (Receipt)
- **Input**: Observation object
- **Security Controls**: Access control, capability verification, audit logging
- **Output**: Access receipt with cryptographic proof
- **Performance Target**: < 500ms retrieval time

### Stage 3: Plan (DSL)
- **Input**: Access receipt and observation
- **Security Controls**: Plan validation, resource limits, sandbox constraints
- **Output**: Execution plan in domain-specific language
- **Performance Target**: < 200ms planning time

### Stage 4: Kernel Decision
- **Input**: Execution plan and context
- **Security Controls**: Cryptographic verification, policy enforcement, isolation
- **Output**: Decision with cryptographic proof
- **Performance Target**: < 1s decision time

### Stage 5: Tool Broker
- **Input**: Kernel decision and execution plan
- **Security Controls**: Sandbox execution, resource monitoring, output validation
- **Output**: Tool execution results
- **Performance Target**: < 5s execution time

### Stage 6: Egress (Certificate)
- **Input**: Tool execution results and decision
- **Security Controls**: Output validation, certificate generation, integrity checks
- **Output**: Egress certificate with cryptographic proof
- **Performance Target**: < 300ms certificate generation

### Stage 7: Safety Case
- **Input**: All stage outputs and proofs
- **Security Controls**: Bundle verification, hash validation, retention policy
- **Output**: Comprehensive safety case bundle
- **Performance Target**: < 500ms bundle generation

## Security Architecture

### Cryptographic Foundation

The system uses multiple cryptographic primitives to ensure security:

- **Ed25519**: Digital signatures for authentication and non-repudiation
- **BLAKE3**: Fast cryptographic hashing for integrity verification
- **AES-256-GCM**: Symmetric encryption for data at rest and in transit
- **ChaCha20-Poly1305**: High-performance authenticated encryption

### Isolation Mechanisms

- **Process Isolation**: Each tool execution runs in isolated containers
- **Memory Isolation**: Separate memory spaces for different security domains
- **Network Isolation**: Controlled network access with firewall rules
- **Resource Limits**: CPU, memory, and disk usage constraints

### Access Control

- **Capability-Based Security**: Fine-grained permissions through capabilities
- **Role-Based Access Control**: Hierarchical permission management
- **Multi-Factor Authentication**: Multiple authentication factors required
- **Session Management**: Secure session handling with timeouts

## SLO Thresholds

### Performance SLOs

| Metric | Threshold | Measurement Method | k6 Job Configuration |
|--------|-----------|-------------------|---------------------|
| P95 Latency | ≤ 2 seconds | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| P99 Latency | ≤ 5 seconds | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| Error Rate | ≤ 2% | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| Throughput | ≥ 100 req/s | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| Availability | ≥ 99.9% | Uptime monitoring | Prometheus + Grafana |

### Security SLOs

| Metric | Threshold | Measurement Method | Validation |
|--------|-----------|-------------------|------------|
| Cross-tenant interactions | 0 | Audit logging | Red-team testing |
| Data leaks | 0 | Content analysis | Automated scanning |
| Authentication bypass | 0 | Penetration testing | OWASP ZAP |
| Injection attacks | 0 | Vulnerability scanning | SAST + DAST |

### Cost SLOs

| Metric | Threshold | Measurement Method | Optimization |
|--------|-----------|-------------------|--------------|
| CPU per 1k calls | ≤ 0.05 cores | Resource monitoring | Performance optimization |
| Memory per 1k calls | ≤ 512 MB | Resource monitoring | Memory optimization |
| Cost per 1k transactions | ≤ $0.05 | Cost tracking | Infrastructure optimization |

## Non-Interference Statement

**Provability Fabric Testbed Non-Interference Guarantee**

The Provability Fabric Testbed implements strict isolation mechanisms that guarantee non-interference between different tenants and security domains. This means:

1. **Tenant Isolation**: No tenant can access, modify, or observe data from other tenants
2. **Process Isolation**: Each execution runs in isolated containers with no shared state
3. **Memory Isolation**: Separate memory spaces prevent data leakage between processes
4. **Network Isolation**: Controlled network access prevents unauthorized communication
5. **Resource Isolation**: CPU, memory, and disk usage are strictly limited per tenant

**Mathematical Guarantee**: The system implements information flow control that satisfies the non-interference property: if two executions differ only in high-security inputs, their low-security outputs must be identical.

**Verification**: Non-interference is verified through:
- Formal verification of isolation mechanisms
- Automated testing of boundary conditions
- Red-team penetration testing
- Continuous monitoring and alerting

## Certificate Examples

### Access Receipt Certificate

```json
{
  "certificate_type": "access_receipt",
  "certificate_id": "receipt_abc123def456",
  "tenant_id": "tenant_xyz789",
  "resource": "/api/data/user_profile",
  "action": "read",
  "capabilities": ["data_access", "user_read"],
  "timestamp": "2024-12-01T10:00:00Z",
  "expires_at": "2024-12-01T11:00:00Z",
  "signature": {
    "algorithm": "ed25519",
    "public_key": "04a1b2c3d4e5f6...",
    "signature": "a1b2c3d4e5f6...",
    "nonce": "nonce_123456789"
  },
  "hash": "sha256:abc123def456...",
  "metadata": {
    "request_id": "req_123456",
    "user_agent": "pf-agent/1.0.0",
    "ip_address": "192.168.1.100"
  }
}
```

### Kernel Decision Certificate

```json
{
  "certificate_type": "kernel_decision",
  "certificate_id": "decision_xyz789abc123",
  "request_id": "req_123456",
  "decision": "allowed",
  "reasoning": "User has valid capabilities and request meets policy requirements",
  "timestamp": "2024-12-01T10:00:01Z",
  "policy_version": "1.2.3",
  "risk_score": 0.1,
  "confidence": 0.95,
  "signature": {
    "algorithm": "ed25519",
    "public_key": "04f6e5d4c3b2a1...",
    "signature": "f6e5d4c3b2a1...",
    "nonce": "nonce_987654321"
  },
  "hash": "sha256:xyz789abc123...",
  "execution_plan": {
    "plan_id": "plan_456789",
    "tools": ["data_retriever", "validator"],
    "resource_limits": {
      "cpu": "0.1",
      "memory": "128Mi",
      "timeout": "30s"
    }
  }
}
```

### Egress Certificate

```json
{
  "certificate_type": "egress_certificate",
  "certificate_id": "egress_def456ghi789",
  "request_id": "req_123456",
  "output_hash": "sha256:def456ghi789...",
  "timestamp": "2024-12-01T10:00:05Z",
  "valid_from": "2024-12-01T10:00:05Z",
  "valid_until": "2024-12-01T11:00:05Z",
  "issuer": "pf-kernel",
  "signature": {
    "algorithm": "ed25519",
    "public_key": "04a1b2c3d4e5f6...",
    "signature": "a1b2c3d4e5f6...",
    "nonce": "nonce_456789123"
  },
  "integrity_checks": {
    "data_hash": "sha256:data123...",
    "metadata_hash": "sha256:meta456...",
    "timestamp_hash": "sha256:time789..."
  },
  "audit_trail": {
    "access_receipt_id": "receipt_abc123def456",
    "kernel_decision_id": "decision_xyz789abc123",
    "tool_execution_id": "exec_123456789"
  }
}
```

### Safety Case Bundle

```json
{
  "bundle_type": "safety_case",
  "bundle_id": "bundle_ghi789jkl012",
  "session_id": "session_abc123",
  "timestamp": "2024-12-01T10:00:06Z",
  "bundle_version": "1.0.0",
  "components": {
    "access_receipt": "receipt_abc123def456",
    "kernel_decision": "decision_xyz789abc123",
    "egress_certificate": "egress_def456ghi789",
    "execution_plan": "plan_456789",
    "tool_results": "results_789012"
  },
  "manifest": {
    "manifest_version": "1.0.0",
    "generated_at": "2024-12-01T10:00:06Z",
    "files": {
      "access_receipt.json": {
        "hash": "sha256:abc123...",
        "size": 1024,
        "modified": "2024-12-01T10:00:00Z"
      },
      "kernel_decision.json": {
        "hash": "sha256:xyz789...",
        "size": 2048,
        "modified": "2024-12-01T10:00:01Z"
      },
      "egress_certificate.json": {
        "hash": "sha256:def456...",
        "size": 1536,
        "modified": "2024-12-01T10:00:05Z"
      }
    }
  },
  "retention_policy": {
    "retention_days": 90,
    "expires_at": "2025-03-01T10:00:06Z",
    "auto_delete": true
  }
}
```

## Performance Headers

The system exposes performance timing headers for monitoring and debugging:

- `X-PF-Plan-ms`: Time spent in planning stage (milliseconds)
- `X-PF-Retrieval-ms`: Time spent in retrieval stage (milliseconds)
- `X-PF-Kernel-ms`: Time spent in kernel decision stage (milliseconds)
- `X-PF-Egress-ms`: Time spent in egress certificate generation (milliseconds)

These headers enable real-time performance monitoring and help identify bottlenecks in the decision path.

## Security Monitoring

### Real-Time Alerts

- **Authentication Failures**: Multiple failed authentication attempts
- **Rate Limit Violations**: Excessive request rates from single sources
- **Policy Violations**: Requests that violate security policies
- **Resource Exhaustion**: CPU, memory, or disk usage approaching limits
- **Anomalous Behavior**: Unusual patterns in request processing

### Audit Logging

All system activities are logged with the following information:
- Timestamp and request ID
- User/tenant identification
- Resource accessed and action performed
- Decision outcome and reasoning
- Performance metrics and timing
- Cryptographic proofs and signatures

### Compliance Reporting

The system generates comprehensive compliance reports including:
- Access control compliance
- Data protection compliance
- Audit trail completeness
- Performance SLO compliance
- Security incident reports
