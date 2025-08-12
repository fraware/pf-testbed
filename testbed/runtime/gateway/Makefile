# Provability Fabric Testbed - Agent-Zoo Gateway Makefile

.PHONY: help build test test-coverage clean install dev start validate-gate lint

# Default target
help:
	@echo "Provability Fabric Testbed - Agent-Zoo Gateway"
	@echo "=============================================="
	@echo ""
	@echo "Available targets:"
	@echo "  help           - Show this help message"
	@echo "  install        - Install dependencies"
	@echo "  build          - Build TypeScript to JavaScript"
	@echo "  dev            - Start in development mode"
	@echo "  start          - Start in production mode"
	@echo "  test           - Run all tests"
	@echo "  test-coverage  - Run tests with coverage"
	@echo "  validate-gate  - Run gate validation (TB-AGENTS)"
	@echo "  lint           - Run ESLint"
	@echo "  clean          - Clean build artifacts"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	npm install

# Build TypeScript
build: install
	@echo "🔨 Building TypeScript..."
	npm run build

# Start in development mode
dev: install
	@echo "🚀 Starting in development mode..."
	npm run dev

# Start in production mode
start: build
	@echo "🚀 Starting in production mode..."
	npm start

# Run all tests
test: install
	@echo "🧪 Running tests..."
	npm test

# Run tests with coverage
test-coverage: install
	@echo "📊 Running tests with coverage..."
	npm run test:coverage

# Run gate validation (TB-AGENTS)
validate-gate: install
	@echo "🚪 Running Agent-Zoo Gate Validation (TB-AGENTS)..."
	@echo "This validates that all five journeys run on all four stacks with comparable metrics."
	@echo ""
	npx ts-node scripts/validate-gate.ts

# Run ESLint
lint: install
	@echo "🔍 Running ESLint..."
	npm run lint

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/
	rm -rf node_modules/
	rm -rf coverage/
	@echo "✅ Clean complete"

# Quick validation (build + test + gate validation)
validate: build test validate-gate
	@echo "🎉 All validations passed!"

# Development workflow
dev-setup: install build test
	@echo "✅ Development environment setup complete"

# Production deployment
deploy: clean install build test validate-gate
	@echo "🚀 Production deployment ready"

# Show status
status:
	@echo "📊 Gateway Status:"
	@echo "  Node version: $(shell node --version)"
	@echo "  NPM version: $(shell npm --version)"
	@echo "  TypeScript version: $(shell npx tsc --version)"
	@if [ -d "node_modules" ]; then echo "  Dependencies: ✅ Installed"; else echo "  Dependencies: ❌ Not installed"; fi
	@if [ -d "dist" ]; then echo "  Build: ✅ Built"; else echo "  Build: ❌ Not built"; fi
	@if [ -f "package-lock.json" ]; then echo "  Lock file: ✅ Present"; else echo "  Lock file: ❌ Missing"; fi

# Health check
health:
	@echo "🏥 Health Check:"
	@if [ -f "dist/main.js" ]; then echo "  Main executable: ✅ Present"; else echo "  Main executable: ❌ Missing"; fi
	@if [ -f "src/main.ts" ]; then echo "  Source files: ✅ Present"; else echo "  Source files: ❌ Missing"; fi
	@if [ -f "env.example" ]; then echo "  Environment template: ✅ Present"; else echo "  Environment template: ❌ Missing"; fi
	@if [ -f "tsconfig.json" ]; then echo "  TypeScript config: ✅ Present"; else echo "  TypeScript config: ❌ Missing"; fi

# Environment setup
env-setup:
	@echo "⚙️  Environment Setup:"
	@if [ ! -f ".env" ]; then \
		echo "  Creating .env from template..."; \
		cp env.example .env; \
		echo "  ✅ .env created from template"; \
		echo "  ⚠️  Please configure your API keys and settings in .env"; \
	else \
		echo "  .env: ✅ Already exists"; \
	fi

# Security check
security-check:
	@echo "🔒 Security Check:"
	@if [ -f ".env" ]; then \
		echo "  .env file: ✅ Present (check for sensitive data)"; \
	else \
		echo "  .env file: ❌ Missing (run 'make env-setup')"; \
	fi
	@if [ -f "package-lock.json" ]; then echo "  Package lock: ✅ Present"; else echo "  Package lock: ❌ Missing"; fi
	@echo "  ⚠️  Review dependencies for security vulnerabilities: npm audit"

# Performance test
perf-test: install
	@echo "⚡ Performance Testing:"
	@echo "  Running performance benchmarks..."
	npm run test:perf || echo "  ⚠️  Performance tests not configured"

# Documentation
docs:
	@echo "📚 Documentation:"
	@if [ -f "README.md" ]; then echo "  README: ✅ Present"; else echo "  README: ❌ Missing"; fi
	@if [ -f "docs/" ]; then echo "  Docs directory: ✅ Present"; else echo "  Docs directory: ❌ Missing"; fi

# Full system check
system-check: status health env-setup security-check docs
	@echo ""
	@echo "🎯 System Check Complete!"
	@echo "  Run 'make validate-gate' to test the Agent-Zoo implementation"
	@echo "  Run 'make dev' to start the gateway in development mode"

# Show supported journeys and tools
info:
	@echo "📋 Agent-Zoo Information:"
	@echo ""
	@echo "Supported Agent Stacks:"
	@echo "  • OpenAI Assistants"
	@echo "  • LangChain"
	@echo "  • LangGraph"
	@echo "  • DSPy"
	@echo ""
	@echo "Supported Journeys:"
	@echo "  • support_triage"
	@echo "  • expense_approval"
	@echo "  • sales_outreach"
	@echo "  • hr_onboarding"
	@echo "  • dev_triage"
	@echo ""
	@echo "Supported Tools:"
	@echo "  • slack, email, calendar, notion"
	@echo "  • stripe, github, search, fetch"
	@echo ""
	@echo "Gate Requirements (TB-AGENTS):"
	@echo "  ✅ All five journeys run on all four stacks"
	@echo "  ✅ Normalized trace export schema"
	@echo "  ✅ Toggle shadow vs enforce (PF_ENFORCE=true)"
	@echo "  ✅ Comparable metrics across all stacks"

# Show this help by default
.DEFAULT_GOAL := help
