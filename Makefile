.PHONY: help build-docker run-docker stop-docker helm-install helm-uninstall

# Default target
help:
	@echo "Steam Librarian - Available targets:"
	@echo "  make build-docker    - Build Docker images"
	@echo "  make run-docker      - Run with Docker Compose"
	@echo "  make stop-docker     - Stop Docker Compose"
	@echo "  make helm-install    - Install with Helm (requires values-override.yaml)"
	@echo "  make helm-uninstall  - Uninstall Helm release"
	@echo "  make helm-lint       - Lint Helm chart"

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

# Helm targets
helm-lint:
	@echo "Linting Helm chart..."
	helm lint deploy/helm/steam-librarian

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
test:
	@echo "Running tests..."
	python -m pytest tests/

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f steam_library.db