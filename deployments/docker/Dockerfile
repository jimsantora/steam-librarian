# Multi-stage Docker build for Steam Librarian
# This Dockerfile builds both the web server and MCP server binaries

# Build stage
FROM golang:1.21-alpine AS builder

# Install necessary packages
RUN apk add --no-cache git ca-certificates tzdata

# Set working directory
WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the web server binary
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o web-server ./cmd/web-server

# Build the MCP server binary
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o mcp-server ./cmd/mcp-server

# Production stage for web server
FROM alpine:latest AS web-server

# Install ca-certificates for HTTPS calls and sqlite for database
RUN apk --no-cache add ca-certificates sqlite

WORKDIR /root/

# Copy the web server binary from builder stage
COPY --from=builder /app/web-server .

# Copy configuration files
COPY --from=builder /app/configs ./configs

# Copy web assets
COPY --from=builder /app/web ./web

# Create directory for SQLite database
RUN mkdir -p /data

# Expose port 8080
EXPOSE 8080

# Set environment variables for production
ENV GIN_MODE=release
ENV DATABASE_TYPE=sqlite
ENV DATABASE_FILE_PATH=/data/steam_librarian.db
ENV SERVER_ENVIRONMENT=production

# Run the web server
CMD ["./web-server"]

# Production stage for MCP server
FROM alpine:latest AS mcp-server

# Install ca-certificates and sqlite
RUN apk --no-cache add ca-certificates sqlite

WORKDIR /root/

# Copy the MCP server binary from builder stage
COPY --from=builder /app/mcp-server .

# Copy configuration files
COPY --from=builder /app/configs ./configs

# Create directory for SQLite database
RUN mkdir -p /data

# Set environment variables for production
ENV DATABASE_TYPE=sqlite
ENV DATABASE_FILE_PATH=/data/steam_librarian.db
ENV MCP_ENABLED=true

# Run the MCP server
CMD ["./mcp-server"]

# Combined stage that includes both servers (for development/testing)
FROM alpine:latest AS combined

# Install ca-certificates, sqlite, and supervisor for running multiple processes
RUN apk --no-cache add ca-certificates sqlite supervisor

WORKDIR /root/

# Copy both binaries from builder stage
COPY --from=builder /app/web-server .
COPY --from=builder /app/mcp-server .

# Copy configuration files
COPY --from=builder /app/configs ./configs

# Copy web assets
COPY --from=builder /app/web ./web

# Create directory for SQLite database
RUN mkdir -p /data

# Create supervisor configuration
RUN mkdir -p /etc/supervisor/conf.d
COPY deployments/docker/supervisord.conf /etc/supervisord.conf

# Expose port 8080 for web server
EXPOSE 8080

# Set environment variables for production
ENV GIN_MODE=release
ENV DATABASE_TYPE=sqlite
ENV DATABASE_FILE_PATH=/data/steam_librarian.db
ENV SERVER_ENVIRONMENT=production
ENV MCP_ENABLED=true

# Run supervisor to manage both processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]