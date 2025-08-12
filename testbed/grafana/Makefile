# Grafana Dashboard Management Makefile
# Auto-loads dashboards and provides automation for observability setup

.PHONY: help up down reload-dashboards test-dashboards clean logs

# Default target
help:
	@echo "Available targets:"
	@echo "  up              - Start Grafana and Prometheus services"
	@echo "  down            - Stop all services"
	@echo "  reload-dashboards - Reload all dashboard configurations"
	@echo "  test-dashboards - Run Cypress tests against dashboards"
	@echo "  clean           - Clean up temporary files"
	@echo "  logs            - Show service logs"

# Start services
up:
	@echo "Starting observability services..."
	docker-compose -f docker-compose.yml up -d
	@echo "Waiting for services to be ready..."
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Services will be ready in 30 seconds..."

# Stop services
down:
	@echo "Stopping services..."
	docker-compose -f docker-compose.yml down
	@echo "Services stopped"

# Reload dashboard configurations
reload-dashboards:
	@echo "Reloading dashboard configurations..."
	@if [ -d "dashboards" ]; then \
		for dashboard in dashboards/*.json; do \
			if [ -f "$$dashboard" ]; then \
				echo "Loading $$dashboard..."; \
				curl -X POST \
					-H "Content-Type: application/json" \
					-H "Authorization: Bearer $(shell cat .grafana-token 2>/dev/null || echo '')" \
					-d @$$dashboard \
					"http://localhost:3000/api/dashboards/db" \
					2>/dev/null | jq -r '.status // "Failed"' | grep -q "success" && \
					echo "✓ $$dashboard loaded successfully" || \
					echo "✗ Failed to load $$dashboard"; \
			fi; \
		done; \
	else \
		echo "No dashboards directory found"; \
	fi

# Test dashboards with Cypress
test-dashboards:
	@echo "Running dashboard tests with Cypress..."
	@if command -v cypress >/dev/null 2>&1; then \
		cd .. && npm run cypress:run -- --spec "tests/ui/observability.cy.ts"; \
	else \
		echo "Cypress not found. Installing..."; \
		cd .. && npm install cypress --save-dev; \
		npx cypress run --spec "tests/ui/observability.cy.ts"; \
	fi

# Clean up temporary files
clean:
	@echo "Cleaning up temporary files..."
	rm -f .grafana-token
	rm -f dashboards/*.tmp
	@echo "Cleanup complete"

# Show service logs
logs:
	@echo "Showing service logs..."
	docker-compose -f docker-compose.yml logs -f

# Setup Grafana API token
setup-token:
	@echo "Setting up Grafana API token..."
	@echo "Please create an API token in Grafana and save it to .grafana-token file"
	@echo "Or run: echo 'your-token-here' > .grafana-token"

# Verify dashboard configurations
verify-dashboards:
	@echo "Verifying dashboard configurations..."
	@for dashboard in dashboards/*.json; do \
		if [ -f "$$dashboard" ]; then \
			echo "Verifying $$dashboard..."; \
			if jq empty "$$dashboard" 2>/dev/null; then \
				echo "✓ $$dashboard is valid JSON"; \
			else \
				echo "✗ $$dashboard has invalid JSON"; \
			fi; \
		fi; \
	done

# Export dashboard configurations
export-dashboards:
	@echo "Exporting dashboard configurations..."
	@mkdir -p exports
	@if [ -f ".grafana-token" ]; then \
		curl -H "Authorization: Bearer $(shell cat .grafana-token)" \
			"http://localhost:3000/api/search" | \
		jq -r '.[] | select(.type == "dash-db") | .uid' | \
		while read uid; do \
			curl -H "Authorization: Bearer $(shell cat .grafana-token)" \
				"http://localhost:3000/api/dashboards/uid/$$uid" | \
			jq '.dashboard' > "exports/$$uid.json"; \
			echo "Exported dashboard $$uid"; \
		done; \
	else \
		echo "No Grafana token found. Run 'make setup-token' first."; \
	fi

# Health check
health-check:
	@echo "Checking service health..."
	@echo "Grafana: $$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health || echo "DOWN")"
	@echo "Prometheus: $$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/-/healthy || echo "DOWN")"

# Install dependencies
install-deps:
	@echo "Installing dependencies..."
	@if [ -f "package.json" ]; then \
		npm install; \
	else \
		echo "No package.json found"; \
	fi

# Run all tests
test: test-dashboards
	@echo "All tests completed"

# Full setup
setup: install-deps up setup-token reload-dashboards
	@echo "Setup complete! Run 'make test' to verify everything works."

# Development mode
dev: up
	@echo "Development mode started. Services are running."
	@echo "Run 'make reload-dashboards' after making changes to dashboards."
	@echo "Run 'make test-dashboards' to test changes."
	@echo "Run 'make down' to stop services."

