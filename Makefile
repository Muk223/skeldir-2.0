.PHONY: help contracts-check contracts-validate contracts-check-auth contracts-check-attribution models-generate mocks-start mocks-stop mocks-restart tests-integration backend-test frontend-test

help: ## Show this help message
	@echo "SKELDIR 2.0 Monorepo - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

contracts-check: ## Bundle and validate all OpenAPI contracts (recommended)
	@echo "Running contract validation pipeline..."
	@bash scripts/contracts/check.sh

contracts-check-smoke: ## Bundle, validate, and run model generation smoke test
	@echo "Running contract validation with model generation smoke test..."
	@bash scripts/contracts/check.sh smoke

contracts-check-auth: ## Bundle and validate auth contract only
	@bash scripts/contracts/check.sh false auth

contracts-check-attribution: ## Bundle and validate attribution contract only
	@bash scripts/contracts/check.sh false attribution

contracts-validate: ## Validate all OpenAPI contracts (legacy - use contracts-check instead)
	@echo "Validating OpenAPI contracts..."
	@for file in api-contracts/openapi/v1/**/*.yaml api-contracts/openapi/v1/_common/*.yaml; do \
		if [ -f "$$file" ]; then \
			echo "Validating $$file..."; \
			npx @openapitools/openapi-generator-cli validate -i "$$file" || exit 1; \
		fi; \
	done
	@echo "All contracts validated successfully"

models-generate: ## Generate Pydantic models from contracts
	@echo "Generating Pydantic models..."
	@bash scripts/generate-models.sh

mocks-start: ## Start all Prism mock servers
	@echo "Starting mock servers..."
	@bash scripts/start-mocks.sh

mocks-stop: ## Stop all Prism mock servers
	@echo "Stopping mock servers..."
	@bash scripts/stop-mocks.sh

mocks-restart: ## Restart all Prism mock servers
	@echo "Restarting mock servers..."
	@bash scripts/restart-mocks.sh all

tests-integration: ## Run Playwright integration tests
	@echo "Running integration tests..."
	@npx playwright test

backend-test: ## Run backend unit tests
	@echo "Running backend tests..."
	@cd backend && pytest

frontend-test: ## Run frontend tests
	@echo "Running frontend tests..."
	@cd frontend && npm test

install: ## Install all dependencies
	@echo "Installing root dependencies..."
	@npm install
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt || echo "Backend requirements.txt not found"
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install || echo "Frontend package.json not found"

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov
	@rm -rf frontend/node_modules frontend/.next frontend/dist frontend/build
	@rm -rf test-results playwright-report
	@rm -rf tmp/

contract-check-conformance: ## Check contract-implementation conformance
	@echo "Checking contract-implementation conformance..."
	@python scripts/contracts/dump_routes.py
	@python scripts/contracts/dump_contract_ops.py
	@python scripts/contracts/check_static_conformance.py

contract-test-dynamic: ## Run dynamic contract tests
	@echo "Running dynamic contract tests..."
	@cd tests/contract && pytest test_contract_semantics.py -v

contract-enforce-full: ## Run full enforcement pipeline
	@echo "Running full contract enforcement pipeline..."
	@$(MAKE) contract-check-conformance
	@$(MAKE) contract-test-dynamic
	@echo "✅ Contract enforcement complete"

contract-print-scope: ## Print route classification
	@python scripts/contracts/print_scope_routes.py

contract-integrity: ## Run contract integrity tests (mocks vs contracts)
	@echo "Running contract integrity tests..."
	@cd tests/contract && pytest test_mock_integrity.py -v

contract-provider: ## Run provider contract tests (implementation vs contracts)
	@echo "Running provider contract tests..."
	@cd tests/contract && pytest test_contract_semantics.py -v

contract-full: ## Run full contract pipeline (bundle -> integrity -> provider -> docs)
	@echo "Running full contract enforcement pipeline..."
	@bash scripts/contracts/bundle.sh
	@$(MAKE) contract-integrity
	@$(MAKE) contract-provider
	@echo "✅ Full contract pipeline complete"

domain-map: ## Print domain mapping for mock servers
	@python scripts/contracts/print_domain_map.py

mocks-switch: ## Switch on-demand mock (usage: make mocks-switch DOMAIN=reconciliation)
	@bash scripts/switch-mock.sh $(DOMAIN)

docs-build: ## Build API documentation from contracts
	@echo "Building API documentation..."
	@bash scripts/contracts/build_docs.sh

docs-validate: ## Validate built documentation
	@echo "Validating API documentation..."
	@python scripts/contracts/validate_docs.py

docs-view: ## Open documentation index in browser
	@echo "Opening documentation..."
	@open api-contracts/dist/docs/v1/index.html || xdg-open api-contracts/dist/docs/v1/index.html || start api-contracts/dist/docs/v1/index.html

