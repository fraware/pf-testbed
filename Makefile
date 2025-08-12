# Provability Fabric Testbed Makefile
# 
# Usage:
#   make testbed-up      # Deploy testbed infrastructure
#   make testbed-down    # Destroy testbed infrastructure
#   make testbed-status  # Show testbed status
#   make testbed-logs    # Show testbed logs

.PHONY: help testbed-up testbed-down testbed-status testbed-logs testbed-clean

# Default target
help:
	@echo "Provability Fabric Testbed Management"
	@echo ""
	@echo "Available targets:"
	@echo "  testbed-up      - Deploy testbed infrastructure (<15 min target)"
	@echo "  testbed-down    - Destroy testbed infrastructure"
	@echo "  testbed-status  - Show testbed status"
	@echo "  testbed-logs    - Show testbed logs"
	@echo "  testbed-clean   - Clean up local artifacts"
	@echo "  help            - Show this help message"

# Check if required tools are installed
check-tools:
	@command -v terraform >/dev/null 2>&1 || { echo "terraform is required but not installed. Aborting." >&2; exit 1; }
	@command -v gcloud >/dev/null 2>&1 || { echo "gcloud is required but not installed. Aborting." >&2; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed. Aborting." >&2; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "helm is required but not installed. Aborting." >&2; exit 1; }

# Initialize Terraform
terraform-init:
	@echo "Initializing Terraform..."
	cd ops/terraform/testbed && terraform init

# Deploy testbed infrastructure
testbed-up: check-tools terraform-init
	@echo "🚀 Deploying Provability Fabric Testbed..."
	@echo "Target: <15 minutes deployment time"
	@echo ""
	
	# Set start time for timing
	@echo "Start time: $$(date)"
	@START_TIME=$$(date +%s)
	
	# Deploy infrastructure
	@echo "📦 Deploying GKE cluster and networking..."
	cd ops/terraform/testbed && terraform apply -auto-approve
	
	# Get cluster credentials
	@echo "🔑 Getting cluster credentials..."
	@CLUSTER_NAME=$$(cd ops/terraform/testbed && terraform output -raw cluster_name)
	@CLUSTER_ZONE=$$(cd ops/terraform/testbed && terraform output -raw cluster_endpoint | sed 's/.*\/\///' | sed 's/:.*//')
	@gcloud container clusters get-credentials $$CLUSTER_NAME --zone=$$CLUSTER_ZONE
	
	# Deploy Kubernetes resources
	@echo "⚙️  Deploying Kubernetes resources..."
	kubectl apply -f ops/k8s/base/
	
	# Deploy monitoring stack
	@echo "📊 Deploying monitoring stack..."
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo add grafana https://grafana.github.io/helm-charts
	helm repo update
	
	# Install Prometheus
	helm install prometheus prometheus-community/kube-prometheus-stack \
		--namespace monitoring \
		--create-namespace \
		--set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
		--set grafana.enabled=true \
		--set grafana.adminPassword=admin123
	
	# Wait for pods to be ready
	@echo "⏳ Waiting for pods to be ready..."
	kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s
	kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s
	
	# Deploy testbed components
	@echo "🔧 Deploying testbed components..."
	kubectl apply -f ops/k8s/testbed/overlays/
	
	# Wait for testbed to be ready
	@echo "⏳ Waiting for testbed to be ready..."
	kubectl wait --for=condition=ready pod -l app=pf-system -n pf-system --timeout=300s
	
	# Calculate deployment time
	@END_TIME=$$(date +%s)
	@DEPLOYMENT_TIME=$$((END_TIME - START_TIME))
	@MINUTES=$$((DEPLOYMENT_TIME / 60))
	@SECONDS=$$((DEPLOYMENT_TIME % 60))
	
	@echo ""
	@echo "✅ Testbed deployment completed!"
	@echo "⏱️  Total deployment time: $$MINUTES minutes $$SECONDS seconds"
	
	# Show status
	@echo ""
	@echo "📊 Testbed Status:"
	kubectl get pods --all-namespaces | grep -E "(pf-system|agents|acme|globex|monitoring)"
	
	@echo ""
	@echo "🌐 Access URLs:"
	@echo "  Grafana: http://localhost:3000 (admin/admin123)"
	@echo "  Prometheus: http://localhost:9090"
	
	@echo ""
	@echo "🔍 To check testbed status: make testbed-status"
	@echo "📝 To view logs: make testbed-logs"
	@echo "🗑️  To destroy: make testbed-down"

# Destroy testbed infrastructure
testbed-down: check-tools
	@echo "🗑️  Destroying Provability Fabric Testbed..."
	
	# Remove Kubernetes resources
	@echo "🧹 Removing Kubernetes resources..."
	kubectl delete -f ops/k8s/testbed/overlays/ --ignore-not-found=true
	kubectl delete -f ops/k8s/base/ --ignore-not-found=true
	
	# Remove monitoring stack
	@echo "📊 Removing monitoring stack..."
	helm uninstall prometheus -n monitoring --ignore-not-found=true
	kubectl delete namespace monitoring --ignore-not-found=true
	
	# Destroy infrastructure
	@echo "🏗️  Destroying infrastructure..."
	cd ops/terraform/testbed && terraform destroy -auto-approve
	
	@echo "✅ Testbed destroyed successfully!"

# Show testbed status
testbed-status: check-tools
	@echo "📊 Provability Fabric Testbed Status"
	@echo "=================================="
	@echo ""
	
	@echo "🏗️  Infrastructure Status:"
	cd ops/terraform/testbed && terraform show -json | jq -r '.values.outputs | to_entries[] | "  \(.key): \(.value.value)"' 2>/dev/null || echo "  Terraform state not available"
	
	@echo ""
	@echo "⚙️  Kubernetes Resources:"
	@echo "  Namespaces:"
	kubectl get namespaces | grep -E "(pf-system|agents|acme|globex|monitoring)" || echo "    No testbed namespaces found"
	
	@echo ""
	@echo "  Pods:"
	kubectl get pods --all-namespaces | grep -E "(pf-system|agents|acme|globex|monitoring)" || echo "    No testbed pods found"
	
	@echo ""
	@echo "  Services:"
	kubectl get services --all-namespaces | grep -E "(pf-system|agents|acme|globex|monitoring)" || echo "    No testbed services found"
	
	@echo ""
	@echo "🔒 Network Policies:"
	kubectl get networkpolicies --all-namespaces | grep -E "(pf-system|agents|acme|globex)" || echo "    No network policies found"
	
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  Prometheus:"
	kubectl get pods -n monitoring -l app=prometheus 2>/dev/null || echo "    Prometheus not deployed"
	@echo "  Grafana:"
	kubectl get pods -n monitoring -l app=grafana 2>/dev/null || echo "    Grafana not deployed"

# Show testbed logs
testbed-logs: check-tools
	@echo "📝 Provability Fabric Testbed Logs"
	@echo "================================="
	@echo ""
	
	@echo "🔍 pf-system logs:"
	kubectl logs -n pf-system -l app=pf-system --tail=50 2>/dev/null || echo "  No pf-system logs found"
	
	@echo ""
	@echo "🤖 Agent logs:"
	kubectl logs -n agents -l app=agent --tail=50 2>/dev/null || echo "  No agent logs found"
	
	@echo ""
	@echo "🏢 Tenant logs:"
	@echo "  ACME:"
	kubectl logs -n acme -l app=tenant-app --tail=20 2>/dev/null || echo "    No ACME logs found"
	@echo "  Globex:"
	kubectl logs -n globex -l app=tenant-app --tail=20 2>/dev/null || echo "    No Globex logs found"
	
	@echo ""
	@echo "📊 Monitoring logs:"
	@echo "  Prometheus:"
	kubectl logs -n monitoring -l app=prometheus --tail=20 2>/dev/null || echo "    No Prometheus logs found"
	@echo "  Grafana:"
	kubectl logs -n monitoring -l app=grafana --tail=20 2>/dev/null || echo "    No Grafana logs found"

# Clean up local artifacts
testbed-clean:
	@echo "🧹 Cleaning up local artifacts..."
	rm -rf ops/terraform/testbed/.terraform
	rm -rf ops/terraform/testbed/.terraform.lock.hcl
	rm -rf ops/terraform/testbed/terraform.tfstate*
	@echo "✅ Cleanup completed!"

# Validate configuration
validate: check-tools
	@echo "✅ Validating configuration..."
	cd ops/terraform/testbed && terraform validate
	kubectl apply --dry-run=client -f ops/k8s/base/
	@echo "✅ Configuration validation passed!"

# Run security tests
security-test: check-tools
	@echo "🔒 Running security tests..."
	
	@echo "  Testing network policies..."
	kubectl get networkpolicies --all-namespaces | grep -q "default-deny" || (echo "❌ Default deny policies not found"; exit 1)
	
	@echo "  Testing namespace isolation..."
	kubectl get pods -n acme -o jsonpath='{.items[*].metadata.namespace}' | grep -v "acme" && (echo "❌ ACME namespace contamination detected"; exit 1) || echo "✅ ACME namespace isolation OK"
	kubectl get pods -n globex -o jsonpath='{.items[*].metadata.namespace}' | grep -v "globex" && (echo "❌ Globex namespace contamination detected"; exit 1) || echo "✅ Globex namespace isolation OK"
	
	@echo "✅ Security tests passed!"

# Show help for specific target
%:
	@echo "Unknown target '$@'. Run 'make help' for available targets."

.PHONY: help install build test clean start stop docker-build docker-run docker-stop report

help: ## Show this help message
	@echo "Provability Fabric Testbed - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing Node.js dependencies..."
	npm install
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

build: ## Build all TypeScript components
	@echo "Building TypeScript components..."
	npm run build

test: ## Run all tests
	@echo "Running TypeScript tests..."
	npm test
	@echo "Running Python tests..."
	pytest testbed/tools/reporter/

test-e2e: ## Run end-to-end tests
	@echo "Running Cypress E2E tests..."
	npm run test:e2e

lint: ## Run linting
	@echo "Running ESLint..."
	npm run lint
	@echo "Running Python linting..."
	black --check testbed/tools/reporter/
	flake8 testbed/tools/reporter/

lint-fix: ## Fix linting issues
	@echo "Fixing ESLint issues..."
	npm run lint:fix
	@echo "Fixing Python formatting..."
	black testbed/tools/reporter/
	isort testbed/tools/reporter/

start: ## Start all services
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Services started successfully!"

stop: ## Stop all services
	@echo "Stopping all services..."
	docker-compose down

restart: ## Restart all services
	@echo "Restarting all services..."
	$(MAKE) stop
	$(MAKE) start

status: ## Show service status
	@echo "Service Status:"
	docker-compose ps

logs: ## Show service logs
	@echo "Service Logs:"
	docker-compose logs -f

docker-build: ## Build Docker images
	@echo "Building Docker images..."
	npm run docker:build

docker-run: ## Run with Docker Compose
	@echo "Starting services with Docker Compose..."
	npm run docker:run

docker-stop: ## Stop Docker services
	@echo "Stopping Docker services..."
	npm run docker:stop

report: ## Generate testbed report
	@echo "Generating testbed report..."
	npm run report:generate

report-validate: ## Validate generated report
	@echo "Validating report..."
	npm run report:validate

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	npm run clean
	rm -rf reports/
	rm -rf dist/
	rm -rf build/

dev: ## Start development environment
	@echo "Starting development environment..."
	npm run dev

dev-watch: ## Start development with watch mode
	@echo "Starting development with watch mode..."
	npm run dev:watch

setup: ## Initial setup
	@echo "Setting up Provability Fabric Testbed..."
	$(MAKE) install
	$(MAKE) build
	$(MAKE) start
	@echo "Setup complete! Access services at:"
	@echo "  - Grafana Dashboard: http://localhost:3000"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Self-Serve Ingress: http://localhost:3001"
	@echo "  - Testbed Gateway: http://localhost:3003"
	@echo "  - Ledger: http://localhost:3002"
