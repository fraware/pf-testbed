# Quick Start Guide - Provability Fabric Testbed

**Get up and running with the state-of-the-art dependency management system in minutes!**

## **5-Minute Setup**

### **Step 1: Prerequisites Check**
```bash
# Verify Python 3.8+
python --version

# Verify Node.js 18+
node --version

# Verify Git
git --version
```

### **Step 2: Clone & Setup**
```bash
# Clone the repository
git clone https://github.com/provability-fabric/pf-testbed.git
cd pf-testbed

# Install all dependencies (automatically detects your platform)
make deps
```

### **Step 3: Start Services**
```bash
# Start all services
make up

# Verify everything is running
make status
```

### **Step 4: Run Quality Checks**
```bash
# Run comprehensive quality validation
make quality-check

# Generate evidence pack
make evidence
```

**You're ready to go! Access your services at:**
- **Gateway**: http://localhost:3003
- **Ingress**: http://localhost:3001
- **Grafana**: http://localhost:3100
- **Prometheus**: http://localhost:9090

## **Windows Users - Special Instructions**

If you're on Windows, use these commands instead:

```cmd
# Install dependencies
python scripts/manage-deps.py --install

# Start services
run.bat up

# Run quality checks
run.bat test

# Generate evidence
run.bat evidence
```

## **Platform-Specific Setup**

### **macOS Users**
```bash
# Install Homebrew if you haven't
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system tools
brew install k6 terraform

# Then proceed with standard setup
make deps
```

### **Linux Users (Ubuntu/Debian)**
```bash
# Install system tools
sudo apt update
sudo apt install -y k6 terraform

# Then proceed with standard setup
make deps
```

### **Linux Users (RHEL/CentOS)**
```bash
# Install system tools
sudo yum install -y k6 terraform

# Then proceed with standard setup
make deps
```

## **Advanced Quick Start**

### **Option 1: Full System Setup**
```bash
# Install dependencies with security scanning
make deps-audit

# Run comprehensive testing
make ci

# Start services with monitoring
make up

# Generate comprehensive evidence
make evidence
```

### **Option 2: Development Setup**
```bash
# Install development dependencies
make deps

# Setup pre-commit hooks
pre-commit install

# Run development environment
make dev

# Start coding with quality gates enabled
```

### **Option 3: Production-Ready Setup**
```bash
# Install with production optimizations
make deps

# Run security validation
make security-check

# Build production artifacts
make build

# Deploy to target environment
make deploy
```

## **Verify Your Setup**

### **Health Check Commands**
```bash
# Check system requirements
python scripts/manage-deps.py

# Verify services are running
make status

# Check dependency health
make deps-audit

# Run quick tests
make test
```

### **Expected Output**
```
🔍 System Requirements Check:
  ✅ python
  ✅ node
  ✅ npm
  ✅ pip
  ✅ docker
  ✅ k6
  ✅ terraform

📊 Service Status:
Name                Command               State           Ports
pf-gateway          npm start            Up              0.0.0.0:3003->3003/tcp
pf-ingress          npm start            Up              0.0.0.0:3001->3001/tcp
pf-ledger           npm start            Up              0.0.0.0:3002->3002/tcp
grafana             /run.sh              Up              0.0.0.0:3100->3000/tcp
prometheus          /bin/prometheus      Up              0.0.0.0:9090->9090/tcp
```

## **Troubleshooting**

### **Common Issues & Solutions**

#### **1. Dependencies Not Installing**
```bash
# Clean install
make deps-clean

# Check system requirements
python scripts/manage-deps.py

# Manual installation
python scripts/manage-deps.py --install --clean
```

#### **2. Services Not Starting**
```bash
# Check Docker status
docker ps -a

# View service logs
make logs

# Restart services
make down
make up
```

#### **3. Permission Issues**
```bash
# Fix file permissions
chmod +x scripts/manage-deps.py
chmod +x run.bat

# Run with elevated privileges (if needed)
sudo make deps
```

#### **4. Port Conflicts**
```bash
# Check what's using the ports
netstat -tulpn | grep :3003
netstat -tulpn | grep :3001

# Modify docker-compose.yml if needed
# Change ports in the ports section
```

### **Get Help**
```bash
# Show all available commands
make help

# Generate dependency report
make deps-report

# Run diagnostics
python scripts/manage-deps.py --report
```


---

**Ready to explore? Run `make help` to see all available commands!**

**Need help? Check the troubleshooting section or open a GitHub issue.**