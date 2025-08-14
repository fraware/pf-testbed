# Provability Fabric Testbed

**Enterprise-Grade Testbed for Provability Fabric**

[![Dependency Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen)](https://github.com/provability-fabric/pf-testbed/actions)
[![Security Status](https://img.shields.io/badge/security-audited-brightgreen)](https://github.com/provability-fabric/pf-testbed/actions)
[![Platform Support](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/provability-fabric/pf-testbed)

## **Quick Start**

### **Prerequisites**
- Python 3.8+
- Node.js 18+
- Docker (optional)
- Git

### **Installation (Any Platform)**

```bash
# Clone the repository
git clone https://github.com/provability-fabric/pf-testbed.git
cd pf-testbed

# Install dependencies (automatically detects your platform)
make deps

# Or use the advanced dependency manager
python scripts/manage-deps.py --install
```

### **First Run**

```bash
# Start all services
make up

# Run quality checks
make quality-check

# Generate evidence pack
make evidence

# Run security testing
make redteam
```

## **Available Commands**

### **Cross-Platform Commands (make)**
```bash
# Dependency Management
make deps              # Install all dependencies
make deps-clean        # Clean and reinstall
make deps-update       # Update to latest versions
make deps-audit        # Security audit
make deps-report       # Generate dependency report

# Development
make build             # Build all components
make test              # Run all tests
make lint              # Code quality checks
make format            # Format code
make quality-check     # Comprehensive quality validation

# Operations
make up                # Start all services
make down              # Stop all services
make seed              # Seed data and populate indices
make soak              # Load testing and performance validation
make redteam           # Security testing and adversarial validation
make evidence          # Generate evidence pack export
make metering          # Generate billing and usage reports

# CI/CD
make ci                # Run CI pipeline locally
make cd                # Run CD pipeline locally
make deploy            # Deploy to target environment
```

### **Windows-Specific Commands (run.bat)**
```cmd
# Use run.bat for Windows environments
run.bat up             # Start services
run.bat evidence       # Generate evidence
run.bat soak           # Run load tests
run.bat redteam        # Security testing
run.bat metering       # Billing reports
```

## **Architecture**

### **Core Components**
```
pf-testbed/
├── scripts/manage-deps.py      # Advanced dependency manager
├── Makefile                    # Cross-platform build system
├── .github/workflows/          # CI/CD pipeline
├── .pre-commit-config.yaml    # Quality gates
├── docker-compose.yml          # Service orchestration
├── testbed/                    # Core testbed components
├── external/                   # External integrations
└── docs/                       # Comprehensive documentation
```

### **Service Architecture**
- **Gateway Service** - API gateway and routing
- **Ingress Controller** - Self-serve portal
- **Ledger Service** - Blockchain and transaction management
- **Monitoring Stack** - Prometheus, Grafana, and alerting
- **Security Tools** - Redteam testing and vulnerability scanning

## **Contributing**

### **Development Setup**
```bash
# Clone and setup
git clone <repository-url>
cd pf-testbed
make deps
make quality-check

# Development workflow
make build
make test
make format
make lint
```

### **Code Standards**
- **Python** - PEP 8, Black, isort, flake8, mypy
- **JavaScript/TypeScript** - ESLint, Prettier, type checking
- **Testing** - >80% code coverage, comprehensive test suites
- **Documentation** - Clear APIs, examples, and guides

## **Support & Community**

### **Getting Help**
- **Documentation** - Comprehensive guides and examples
- **Issues** - GitHub Issues for bug reports and feature requests
- **Discussions** - Community forums and Q&A
- **Security** - Security@provability-fabric.org for security issues

### **Resources**
- **Quick Start Guide** - `docs/quickstart.md`
- **Dependency Management** - `DEPENDENCY_MANAGEMENT.md`
- **API Documentation** - `docs/api/`
- **Architecture Guide** - `docs/architecture.md`

## **License**

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## **Acknowledgments**

- **Provability Fabric Team** - Core development and architecture
- **Open Source Community** - Dependencies and tools
- **Security Researchers** - Vulnerability reporting and testing
- **Contributors** - Code, documentation, and testing
