# Provability Fabric Testbed

A testbed for validating and demonstrating Provability Fabric's capabilities with observability, safety case management, external agent integration, and automated reporting.

## Repository Structure

```
testbed/
├── agents/                          # AI Agent Implementations
│   ├── openai_assistants/          # OpenAI Assistant integrations
│   ├── langgraph/                  # LangGraph-based agents
│   ├── langchain/                  # LangChain-based agents
│   └── dspy/                       # DSPy-based agents
├── runtime/                         # Core Runtime Components
│   ├── gateway/                     # Main testbed gateway
│   ├── ingress/                     # Self-serve ingress service
│   ├── ledger/                      # Safety case ledger
│   └── egress-firewall/            # Content egress firewall
├── tools/                           # Development and Analysis Tools
│   └── reporter/                    # Automated reporting system
├── scenarios/                       # Business Scenario Implementations
│   ├── support_triage/             # Support ticket triage
│   ├── expense_approval/           # Expense report processing
│   ├── sales_outreach/             # Sales lead qualification
│   ├── hr_onboarding/              # Employee onboarding
│   └── dev_triage/                 # Development issue triage
├── data/                           # Tenant Data and Knowledge Bases
│   ├── acme/                       # ACME Corporation data
│   │   ├── kb/                     # Knowledge base articles
│   │   └── seeds/                  # Seed data for testing
│   └── globex/                     # Globex Corporation data
│       ├── kb/                     # Knowledge base articles
│       └── seeds/                  # Seed data for testing
├── grafana/                        # Grafana Configuration
│   ├── dashboards/                 # Custom dashboard definitions
│   └── provisioning/               # Data source provisioning
├── prometheus/                     # Prometheus Configuration
│   └── scrape_config/              # Service discovery rules
├── ops/                           # Operations and Infrastructure
│   ├── terraform/                  # Infrastructure as Code
│   │   └── testbed/               # Testbed infrastructure
│   └── k8s/                       # Kubernetes Resources
│       ├── base/                   # Base configurations
│       └── overlays/               # Environment overlays
│           └── testbed/            # Testbed-specific configs
├── tests/                          # Test Suites
│   ├── ui/                         # UI/UX tests
│   ├── integration/                # Integration tests
│   ├── performance/                # Performance tests
│   └── security/                   # Security tests
├── chaos/                          # Chaos Engineering
├── accuracy/                       # Accuracy Monitoring
├── cost_perf/                      # Cost Performance Analysis
└── traffic/                        # Traffic Generation
```

## Quick Start

### 1. Environment Setup
```bash
# Copy environment configuration
cp .env.example .env

# Edit .env with your values
# Required: Database credentials, API keys, secrets
```

### 2. Start Services
```bash
# Using Makefile (recommended)
make up

# Or manually
docker-compose up -d
```

### 3. Access Services
- **Testbed Gateway**: http://localhost:3003
- **Self-Serve Ingress**: http://localhost:3001
- **Grafana Dashboard**: http://localhost:3100
- **Prometheus Metrics**: http://localhost:9090
- **Ledger Service**: http://localhost:3002

## Development Workflow

### Using Makefile
```bash
# Quick development commands
make up          # Start all services
make down        # Stop all services
make logs        # View service logs
make test        # Run all tests
make report      # Generate reports
make clean       # Clean build artifacts

# Full testbed deployment
make testbed-up  # Deploy to Kubernetes
make testbed-down # Destroy testbed
```

### Testing
```bash
# Run specific test suites
npm test                    # TypeScript tests
pytest testbed/tools/      # Python tests
npm run test:e2e          # End-to-end tests
npm run test:observability # Observability tests
```

## Architecture Overview

### Core Components

1. **Gateway Service** - Main API gateway and request routing
2. **Ingress Service** - Self-serve onboarding and authentication
3. **Ledger Service** - Safety case management and audit trails
4. **Egress Firewall** - Content filtering and certificate generation

### Agent Integration

- **OpenAI Assistants** - Direct OpenAI integration
- **LangGraph** - Multi-agent workflows
- **LangChain** - Chain-based processing
- **DSPy** - Prompt optimization

### Security Features

- **PF-Sig Validation** - Provability Fabric signature verification
- **Access Receipts** - Signed audit trails for all operations
- **Tenant Isolation** - Complete data separation
- **Policy Enforcement** - Kernel-based decision enforcement

## Business Scenarios

### Support Triage
Automated support ticket classification and routing with capability verification.

### Expense Approval
Expense report processing with policy compliance and fraud detection.

### Sales Outreach
Lead qualification and personalized outreach with compliance guarantees.

### HR Onboarding
Employee onboarding with document validation and access management.

### Dev Triage
Development issue classification with security assessment.

## Monitoring & Observability

### Metrics
- SLO violations and compliance
- Request latency and throughput
- Theorem verification rates
- Security incident tracking

### Dashboards
- Real-time performance monitoring
- Security alert visualization
- Business metric tracking
- Tenant isolation status

## Contributing

### Development Setup
1. Fork and clone the repository
2. Install dependencies: `npm install && pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Start services: `make up`
5. Run tests: `make test`

### Code Standards
- TypeScript with strict typing
- Python with type hints
- Comprehensive test coverage
- Security-first development
- Documentation-driven design

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Support

For questions and support:
- Create an issue in the repository
- Check the documentation in each component directory
- Review the Postman collection in `docs/postman.json`
- Run `make help` for available commands
