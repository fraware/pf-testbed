# Provability Fabric Testbed

A testbed for validating and demonstrating Provability Fabric's capabilities with observability, safety case management, external agent integration, and automated reporting.

## Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose
- Kubernetes cluster (for production deployment)

### Quick Start

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

3. **Start services**
   ```bash
   # Start Prometheus and Ledger services
   docker-compose up -d
   
   # Start the testbed gateway
   npm run start:gateway
   
   # Start self-serve ingress
   npm run start:ingress
   ```

4. **Access the system**
   - **Testbed Gateway**: http://localhost:3000
   - **Self-Serve Ingress**: http://localhost:3001
   - **Grafana Dashboard**: http://localhost:3000/grafana
   - **Prometheus Metrics**: http://localhost:9090

## Usage Examples

### Observability Dashboard
```typescript
import { observabilityService } from './testbed/runtime/gateway/src/observability';

// Create a trace context
const traceContext = observabilityService.createTraceContext({
  plan_id: 'plan-123',
  tenant: 'acme-corp',
  journey: 'user-onboarding',
  user_id: 'user-456'
});

// Link to Lean theorem
observabilityService.linkLeanTheorem(traceContext.trace_id, {
  theorem_id: 'thm-789',
  theorem_name: 'UserAccessControl',
  spec_file: 'access_control.lean',
  spec_line: 42,
  confidence: 0.95
});
```

### Safety Case Management
```typescript
import { safetyCaseManager } from './testbed/runtime/ledger/safety_case';

// Create safety case bundle
const bundle = safetyCaseManager.createBundle({
  session_id: 'session-123',
  tenant: 'acme-corp',
  plan: planData,
  receipts: [receipt1, receipt2],
  traces: [trace1, trace2]
});

// Export bundle for auditors
const zipBuffer = await safetyCaseManager.exportBundle('session-123');
```

### Self-Serve Agent Integration
```typescript
import { selfServeIngress } from './testbed/ingress/selfserve';

// Start the self-serve service
selfServeIngress.start(3001);

// The service automatically handles:
// - Partner signup and tenant provisioning
// - API key generation and management
// - Rate limiting and tenant isolation
// - PF-Sig and receipt validation
```

### Report Generation
```bash
# Generate comprehensive testbed report
python testbed/tools/reporter/generate_testbed_report.py \
  --config testbed/tools/reporter/config.yaml \
  --output ./reports \
  --format both \
  --time-range 24

# The report includes:
# - Performance metrics (latency, throughput, error rates)
# - Security metrics (SLO violations, honeytoken alerts)
# - Compliance metrics (access receipts, certificates)
# - ART harness comparison
# - Red-team regression analysis
```

## Testing

### Run All Tests
```bash
# Run TypeScript/Node.js tests
npm test

# Run Python tests
pytest testbed/tools/reporter/

# Run Cypress E2E tests
npm run test:e2e

# Run specific testbed tests
npm run test:observability
npm run test:safety-case
npm run test:selfserve
npm run test:reporter
```

### Test Coverage
- **Unit Tests**: Jest for TypeScript, pytest for Python
- **Integration Tests**: API endpoints and service interactions
- **E2E Tests**: Cypress for UI workflows and user journeys
- **Performance Tests**: Latency and throughput validation
- **Security Tests**: Red-team scenarios and vulnerability assessment

## Monitoring & Metrics

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

## Security & Compliance

### Security Features
- **Tenant Isolation**: Complete sandboxing between partners
- **API Key Management**: Secure key generation and rotation
- **Rate Limiting**: Per-tenant request throttling
- **Edge Validation**: PF-Sig and receipt schema verification
- **Honeytokens**: Deception-based security monitoring

### Compliance Frameworks
- **SOC2**: Security controls and monitoring
- **ISO27001**: Information security management
- **GDPR**: Data protection and privacy
- **Audit Trails**: Complete session documentation

### Data Retention
- **Safety Case Bundles**: 90-day retention policy
- **Access Receipts**: Immutable audit logs
- **Kernel Decisions**: Complete decision trail
- **Export Capability**: ZIP format for external review

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
