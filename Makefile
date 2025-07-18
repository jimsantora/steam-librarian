# Steam Librarian Makefile

# Variables
GO_VERSION := 1.21
BINARY_WEB := web-server
BINARY_MCP := mcp-server
DOCKER_IMAGE := steam-librarian
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS := -ldflags "-X main.version=$(VERSION)"

# Default target
.PHONY: help
help:
	@echo "Steam Librarian - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  setup          - Set up development environment"
	@echo "  deps           - Download and verify dependencies"
	@echo "  build          - Build both web and MCP servers"
	@echo "  run-web        - Run web server (requires .env file)"
	@echo "  run-mcp        - Run MCP server (requires .env file)"
	@echo "  dev            - Run web server with auto-reload (requires air)"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run tests"
	@echo "  test-verbose   - Run tests with verbose output"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  lint           - Run linter (requires golangci-lint)"
	@echo ""
	@echo "Building:"
	@echo "  build-web      - Build web server binary"
	@echo "  build-mcp      - Build MCP server binary"
	@echo "  build-all      - Build all binaries for current platform"
	@echo "  build-linux    - Build Linux binaries"
	@echo "  build-windows  - Build Windows binaries"
	@echo "  build-darwin   - Build macOS binaries"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   - Build Docker images"
	@echo "  docker-run     - Run with docker-compose (dev mode)"
	@echo "  docker-prod    - Run with docker-compose (production mode)"
	@echo "  docker-stop    - Stop docker-compose services"
	@echo "  docker-clean   - Clean Docker images and containers"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          - Clean build artifacts"
	@echo "  fmt            - Format Go code"
	@echo "  vet            - Run go vet"
	@echo "  install-tools  - Install development tools"

# Development setup
.PHONY: setup
setup: deps
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from .env.example"; \
		echo "Please edit .env and add your Steam API key"; \
	fi
	@if [ ! -f configs/config.local.yaml ]; then \
		cp configs/config.yaml configs/config.local.yaml; \
		echo "Created configs/config.local.yaml"; \
	fi

.PHONY: deps
deps:
	@echo "Downloading and verifying dependencies..."
	go mod download
	go mod tidy
	go mod verify

# Building
.PHONY: build
build: build-web build-mcp

.PHONY: build-web
build-web:
	@echo "Building web server..."
	CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_WEB) ./cmd/web-server

.PHONY: build-mcp
build-mcp:
	@echo "Building MCP server..."
	CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_MCP) ./cmd/mcp-server

.PHONY: build-all
build-all: build

.PHONY: build-linux
build-linux:
	@echo "Building Linux binaries..."
	GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_WEB)-linux-amd64 ./cmd/web-server
	GOOS=linux GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_MCP)-linux-amd64 ./cmd/mcp-server

.PHONY: build-windows
build-windows:
	@echo "Building Windows binaries..."
	GOOS=windows GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_WEB)-windows-amd64.exe ./cmd/web-server
	GOOS=windows GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_MCP)-windows-amd64.exe ./cmd/mcp-server

.PHONY: build-darwin
build-darwin:
	@echo "Building macOS binaries..."
	GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_WEB)-darwin-amd64 ./cmd/web-server
	GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_MCP)-darwin-amd64 ./cmd/mcp-server
	GOOS=darwin GOARCH=arm64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_WEB)-darwin-arm64 ./cmd/web-server
	GOOS=darwin GOARCH=arm64 CGO_ENABLED=1 go build $(LDFLAGS) -o $(BINARY_MCP)-darwin-arm64 ./cmd/mcp-server

# Running
.PHONY: run-web
run-web: build-web
	@echo "Starting web server..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a && ./$(BINARY_WEB); \
	else \
		echo "No .env file found. Run 'make setup' first."; \
		exit 1; \
	fi

.PHONY: run-mcp
run-mcp: build-mcp
	@echo "Starting MCP server..."
	@if [ -f .env ]; then \
		set -a && . ./.env && set +a && ./$(BINARY_MCP); \
	else \
		echo "No .env file found. Run 'make setup' first."; \
		exit 1; \
	fi

.PHONY: dev
dev:
	@if command -v air > /dev/null; then \
		echo "Starting development server with hot reload..."; \
		air -c .air.toml; \
	else \
		echo "Air not installed. Install with: go install github.com/cosmtrek/air@latest"; \
		echo "Falling back to regular run..."; \
		make run-web; \
	fi

# Testing
.PHONY: test
test:
	@echo "Running tests..."
	go test ./...

.PHONY: test-verbose
test-verbose:
	@echo "Running tests with verbose output..."
	go test -v ./...

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report generated: coverage.html"

.PHONY: lint
lint:
	@if command -v golangci-lint > /dev/null; then \
		echo "Running linter..."; \
		golangci-lint run; \
	else \
		echo "golangci-lint not installed. Install with:"; \
		echo "curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b \$$(go env GOPATH)/bin v1.54.2"; \
	fi

# Docker
.PHONY: docker-build
docker-build:
	@echo "Building Docker images..."
	docker build -f deployments/docker/Dockerfile --target web-server -t $(DOCKER_IMAGE):web-latest .
	docker build -f deployments/docker/Dockerfile --target mcp-server -t $(DOCKER_IMAGE):mcp-latest .
	docker build -f deployments/docker/Dockerfile --target combined -t $(DOCKER_IMAGE):combined-latest .

.PHONY: docker-run
docker-run:
	@echo "Starting development environment with Docker Compose..."
	@if [ ! -f deployments/docker-compose/.env ]; then \
		cp deployments/docker-compose/.env.example deployments/docker-compose/.env; \
		echo "Created .env file in deployments/docker-compose/"; \
		echo "Please edit it and add your Steam API key"; \
		exit 1; \
	fi
	docker-compose -f deployments/docker-compose/docker-compose.dev.yml up -d

.PHONY: docker-prod
docker-prod:
	@echo "Starting production environment with Docker Compose..."
	@if [ ! -f deployments/docker-compose/.env ]; then \
		cp deployments/docker-compose/.env.example deployments/docker-compose/.env; \
		echo "Created .env file in deployments/docker-compose/"; \
		echo "Please edit it and add your Steam API key"; \
		exit 1; \
	fi
	docker-compose -f deployments/docker-compose/docker-compose.yml up -d

.PHONY: docker-stop
docker-stop:
	@echo "Stopping Docker Compose services..."
	docker-compose -f deployments/docker-compose/docker-compose.dev.yml down || true
	docker-compose -f deployments/docker-compose/docker-compose.yml down || true

.PHONY: docker-clean
docker-clean: docker-stop
	@echo "Cleaning Docker images and containers..."
	docker system prune -f
	docker rmi $(DOCKER_IMAGE):web-latest $(DOCKER_IMAGE):mcp-latest $(DOCKER_IMAGE):combined-latest 2>/dev/null || true

# Utilities
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(BINARY_WEB) $(BINARY_MCP)
	rm -f $(BINARY_WEB)-* $(BINARY_MCP)-*
	rm -f *.db *.sqlite *.sqlite3
	rm -f coverage.out coverage.html
	rm -rf dist/

.PHONY: fmt
fmt:
	@echo "Formatting Go code..."
	go fmt ./...

.PHONY: vet
vet:
	@echo "Running go vet..."
	go vet ./...

.PHONY: install-tools
install-tools:
	@echo "Installing development tools..."
	go install github.com/cosmtrek/air@latest
	@echo "Installing golangci-lint..."
	curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin v1.54.2

# Create air config for hot reloading
.PHONY: air-config
air-config:
	@if [ ! -f .air.toml ]; then \
		echo "Creating air configuration..."; \
		cat > .air.toml << 'EOF'; \
root = "."; \
testdata_dir = "testdata"; \
tmp_dir = "air_tmp"; \
; \
[build]; \
  args_bin = []; \
  bin = "./air_tmp/main"; \
  cmd = "go build -o ./air_tmp/main ./cmd/web-server"; \
  delay = 1000; \
  exclude_dir = ["air_tmp", "vendor", "testdata", "deployments", ".git"]; \
  exclude_file = []; \
  exclude_regex = ["_test.go"]; \
  exclude_unchanged = false; \
  follow_symlink = false; \
  full_bin = ""; \
  include_dir = []; \
  include_ext = ["go", "tpl", "tmpl", "html", "yaml", "yml"]; \
  include_file = []; \
  kill_delay = "0s"; \
  log = "build-errors.log"; \
  rerun = true; \
  rerun_delay = 500; \
  send_interrupt = false; \
  stop_on_root = false; \
; \
[color]; \
  app = ""; \
  build = "yellow"; \
  main = "magenta"; \
  runner = "green"; \
  watcher = "cyan"; \
; \
[log]; \
  main_only = false; \
  time = false; \
; \
[misc]; \
  clean_on_exit = false; \
; \
[screen]; \
  clear_on_rebuild = false; \
  keep_scroll = true; \
EOF \
	fi