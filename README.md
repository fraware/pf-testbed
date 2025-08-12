# Provability Fabric Testbed

A comprehensive testbed for validating and demonstrating Provability Fabric's capabilities with observability, safety case management, external agent integration, and automated reporting.

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose
- Kubernetes cluster (for production deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/pf-testbed.git
   cd pf-testbed
   ```

2. **Install dependencies**
   ```bash
   # Install Node.js dependencies
   npm install
   
   # Install Python dependencies
   pip install -r testbed/tools/requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your configuration values
   # Required: Database credentials, API keys, secrets
   ```

4. **Start services**
   ```bash
   # Start all services (Docker Compose)
   run.bat up
   
   # Or use individual commands
   run.bat start:gateway
   run.bat start:ingress
   run.bat start:ledger
   ```

5. **Access the system**
   - **Testbed Gateway**: http://localhost:3003
   - **Self-Serve Ingress**: http://localhost:3001
   - **Grafana Dashboard**: http://localhost:3100
   - **Prometheus Metrics**: http://localhost:9090
   - **Ledger Service**: http://localhost:3002

## Management Commands

### Windows (run.bat)
```cmd
# Quick start (starts all services)
run.bat up

# Stop all services
run.bat down

# View logs
run.bat logs

# Show service status
run.bat status

# Run tests
run.bat test

# Generate reports
run.bat report

# Show help
run.bat
```

### Linux/Mac (Makefile)
```bash
# Quick start (starts all services)
make up

# Stop all services
make down

# View logs
make logs

# Seed data and populate indices
make seed

# Generate testbed report
make report

# Full testbed deployment (Kubernetes)
make testbed-up

# Show help
make help
```

## Architecture Overview

The testbed implements a complete end-to-end decision path with provable security guarantees:

```
┌─────────────┐      ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ Observation │───▶  │   Retrieve   │───▶│    Plan     │───▶│   Kernel    │
│             │      │  (Receipt)   │     │   (DSL)     │     │             │
└─────────────┘      └──────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐      ┌─────────────┐
│ Safety Case │◀───│    Egress    │◀───│ Tool Broker │◀───│  Decision   │
│             │    │   (Cert)     │    │             │      │             │
└─────────────┘    └──────────────┘    └─────────────┘      └─────────────┘
```

## Service Level Objectives (SLOs)

### Performance SLOs
| Metric | Threshold | Measurement Method | k6 Job Configuration |
|--------|-----------|-------------------|---------------------|
| P95 Latency | ≤ 2 seconds | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| P99 Latency | ≤ 5 seconds | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| Error Rate | ≤ 2% | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |
| Throughput | ≥ 100 req/s | Load testing with k6 | `testbed/tests/performance/slo-load-test.js` |

### Security SLOs
| Metric | Threshold | Measurement Method | Validation |
|--------|-----------|-------------------|------------|
| Cross-tenant reads | 0 | Fuzzing tests | 100k queries, 0 violations |
| PII/Secret leaks | 0 | Red-team corpus | 50k adversarial turns |
| Injection blocking | ≥95% | Injection corpus | SQL, XSS, command injection |
| Honeytoken trips | 0 | Production monitoring | Real-time alerting |

### Cost SLOs
| Metric | Threshold | Measurement Method | Optimization |
|--------|-----------|-------------------|-------------|
| CPU/1k calls | ↓ 20-35% | Performance profiling | gRPC, caching, WASM pools |
| Egress latency | p95 < 400ms | Load testing | Streaming detectors, early exit |

## Security Features

### Non-Interference Guarantee
The Provability Fabric Testbed implements strict isolation mechanisms that guarantee non-interference between different tenants and security domains:

- **Tenant Isolation**: Complete sandboxing between partners with physical data partitioning
- **Capability Enforcement**: All tool calls require matching capabilities with cryptographic verification
- **Information Flow Control**: Mathematical guarantees that high-security inputs cannot influence low-security outputs
- **Audit Trails**: Complete session documentation with cryptographic proofs

### Cryptographic Foundation
- **Ed25519**: Digital signatures for authentication and non-repudiation
- **BLAKE3**: Fast cryptographic hashing for integrity verification
- **AES-256-GCM**: Symmetric encryption for data at rest and in transit
- **ChaCha20-Poly1305**: High-performance authenticated encryption

## Testing & Validation

### Run All Tests
```bash
# Run TypeScript/Node.js tests
npm test

# Run Python tests
pytest testbed/tools/reporter/

# Run Cypress E2E tests
npm run test:e2e

# Run specific test suites
npm run test:observability
npm run test:safety-case
npm run test:selfserve
npm run test:reporter
```

### Test Coverage
- **Unit Tests**: Jest for TypeScript, pytest for Python
- **Integration Tests**: API endpoints and service interactions
- **E2E Tests**: Cypress for UI workflows and user journeys
- **Performance Tests**: k6 load testing with SLO validation
- **Security Tests**: Red-team scenarios and vulnerability assessment
- **Fuzzing Tests**: 100k+ queries for cross-tenant isolation validation

## Monitoring & Observability

### Key Performance Indicators
- **Latency to Insight**: < 5 seconds
- **Click-through Performance**: < 2 seconds
- **SLO Violations**: 0 tolerance
- **Bundle Production**: 100% session coverage
- **Agent Onboarding**: < 2 hours to first journey

### Grafana Dashboards
- **SLO Overview**: Real-time violation tracking
- **Latency Metrics**: P95/P99 performance monitoring
- **Theorem Verification**: Lean proof validation rates
- **Active Traces**: Tenant and journey breakdowns
- **Security Alerts**: Honeytoken and certificate status

### Prometheus Metrics
- `testbed_slo_violations_total`: SLO violation counter
- `testbed_request_duration_seconds`: Request latency histogram
- `testbed_theorem_verification_rate`: Theorem verification gauge
- `testbed_active_traces`: Active trace count
- `testbed_honeytoken_alerts`: Security alert counter

## Deployment

### Development Environment
```bash
# Start development services
npm run dev

# Run with hot reload
npm run dev:watch

# Start specific components
npm run start:gateway
npm run start:ingress
npm run start:ledger
```

### Production Deployment
```bash
# Build production artifacts
npm run build

# Deploy to Kubernetes
kubectl apply -f ops/k8s/

# Deploy infrastructure
terraform -chdir=ops/terraform/testbed apply
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or use individual containers
docker run -d --name pf-gateway pf-testbed-gateway:latest
docker run -d --name pf-ingress pf-testbed-ingress:latest
```

## Contributing

### Development Setup
```bash
# Fork and clone
git clone https://github.com/your-username/pf-testbed.git
cd pf-testbed

# Install development dependencies
npm install
pip install -r testbed/tools/requirements.txt

# Set up pre-commit hooks
npm run setup:hooks

# Run linting and formatting
npm run lint
npm run format
```

### Code Standards
- **TypeScript**: Strict mode with comprehensive typing
- **Python**: PEP 8 compliance with type hints
- **Testing**: Minimum 90% code coverage
- **Documentation**: Inline and external documentation
- **Security**: Regular security audits and vulnerability scanning

### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all tests pass
4. Update documentation
5. Submit PR with detailed description
6. Address review feedback
7. Merge after approval

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Provability Fabric Team**: Core platform and architecture
- **Open Source Contributors**: Community-driven improvements
- **Research Partners**: Academic and industry collaboration
- **Early Adopters**: Feedback and real-world testing

---

**Built with ❤️ by the Provability Fabric community**

For more information, visit [provability.fabric](https://github.com/fraware/provability-fabric).
