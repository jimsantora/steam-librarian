.PHONY: help build-docker run-docker stop-docker rebuild-mcp-docker helm-install helm-uninstall lint format-check format test test-unit test-integration test-full check check-full clean

# Default target
help:
	@echo "Steam Librarian - Available targets:"
	@echo "  make build-docker    - Build Docker images"
	@echo "  make run-docker      - Run with Docker Compose"
	@echo "  make stop-docker     - Stop Docker Compose"
	@echo "  make rebuild-mcp-docker - Stop, rebuild MCP server without cache, and run"
	@echo "  make rebuild-all-docker - Stop, rebuild all containers without cache, and run"
	@echo "  make helm-install    - Install with Helm (requires values-override.yaml)"
	@echo "  make helm-uninstall  - Uninstall Helm release"
	@echo "  make helm-lint       - Lint Helm chart"
	@echo "  make helm-validate   - Validate Helm chart with kubeconform"
	@echo "  make lint            - Run ruff linting"
	@echo "  make format-check    - Check code formatting with black"
	@echo "  make format          - Format code with black"
	@echo "  make test            - Run basic import tests"
	@echo "  make test-unit       - Run comprehensive unit tests"
	@echo "  make test-integration- Run integration tests (starts server)"
	@echo "  make test-full       - Run all tests (unit + integration)"
	@echo "  make check           - Run all code quality checks"
	@echo "  make check-full      - Run all checks + comprehensive tests"

# Docker targets
build-docker:
	@echo "Building Docker images..."
	docker build -f deploy/docker/Dockerfile.fetcher -t steam-librarian-fetcher:latest .
	docker build -f deploy/docker/Dockerfile.mcp_server -t steam-librarian-mcp-server:latest .

run-docker:
	@echo "Starting services with Docker Compose..."
	cd deploy/docker && docker-compose up -d

stop-docker:
	@echo "Stopping services..."
	cd deploy/docker && docker-compose down

rebuild-mcp-docker:
	@echo "Stopping services, cleaning images, rebuilding MCP server, and restarting..."
	cd deploy/docker && docker-compose down
	docker image prune -a -f
	docker build --no-cache --pull -f deploy/docker/Dockerfile.mcp_server -t steam-librarian-mcp-server:latest .
	cd deploy/docker && docker-compose up -d mcp-server

rebuild-all-docker:
	@echo "Stopping services, cleaning images, rebuilding MCP server, and restarting..."
	cd deploy/docker && docker-compose down
	docker image prune -a -f
	docker build --no-cache --pull -f deploy/docker/Dockerfile.fetcher -t steam-librarian-fetcher:latest .
	docker build --no-cache --pull -f deploy/docker/Dockerfile.mcp_server -t steam-librarian-mcp-server:latest .
	cd deploy/docker && docker-compose up -d 

# Helm targets
helm-lint:
	@echo "Linting Helm chart..."
	helm lint deploy/helm/steam-librarian

helm-validate:
	@echo "Validating Helm chart with kubeconform..."
	helm template test deploy/helm/steam-librarian \
		--set steam.steamId=test-id \
		--set steam.apiKey=test-key \
		| kubeconform -strict -ignore-missing-schemas

helm-install:
	@echo "Installing Steam Librarian with Helm..."
	@if [ -f deploy/helm/steam-librarian/values-override.yaml ]; then \
		helm install steam-librarian deploy/helm/steam-librarian -f deploy/helm/steam-librarian/values-override.yaml; \
	else \
		echo "ERROR: Please create deploy/helm/steam-librarian/values-override.yaml with your Steam credentials"; \
		exit 1; \
	fi

helm-uninstall:
	@echo "Uninstalling Steam Librarian..."
	helm uninstall steam-librarian

# Development targets
lint:
	@echo "Running ruff linting..."
	ruff check src

format-check:
	@echo "Checking code formatting with black..."
	black --check --diff src

format:
	@echo "Formatting code with black..."
	black src

test:
	@echo "Running basic import tests..."
	python -c "from src.shared.database import Base, get_db; from src.fetcher.steam_library_fetcher import SteamLibraryFetcher; from src.mcp_server.server import mcp; print('✅ All basic imports successful!')"

test-unit:
	@echo "Running comprehensive unit tests..."
	cd $(shell pwd) && PYTHONPATH=src python tests/test_mcp_server.py

test-integration:
	@echo "Running integration tests (this will start a test server)..."
	cd $(shell pwd) && PYTHONPATH=src python tests/test_integration.py

test-full: test-unit test-integration
	@echo "All tests completed!"

check: lint format-check test
	@echo "All checks passed!"

check-full: lint format-check test-full
	@echo "All comprehensive checks and tests passed!"

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f steam_library.db