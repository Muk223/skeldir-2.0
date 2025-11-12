.PHONY: help contracts-validate models-generate mocks-start mocks-stop mocks-restart tests-integration backend-test frontend-test

help: ## Show this help message
	@echo "SKELDIR 2.0 Monorepo - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

contracts-validate: ## Validate all OpenAPI contracts
	@echo "Validating OpenAPI contracts..."
	@for file in contracts/openapi/v1/**/*.yaml contracts/openapi/v1/_common/*.yaml; do \
		if [ -f "$$file" ]; then \
			echo "Validating $$file..."; \
			openapi-generator-cli validate -i "$$file" || exit 1; \
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

