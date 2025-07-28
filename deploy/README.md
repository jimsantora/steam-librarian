# Steam Librarian Deployment Guide

This guide covers deploying Steam Librarian using Docker and Kubernetes (Helm).

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- Steam API credentials

### Quick Start

1. Navigate to the Docker directory:
```bash
cd deploy/docker
```

2. Create your environment file:
```bash
cp .env.example .env
# Edit .env with your Steam credentials
```

3. Build and run the services:
```bash
docker-compose up -d
```

This will:
- Build both the fetcher and MCP server images
- Run the fetcher once to populate the database
- Start the MCP server on port 8000
- Run a cron-like fetcher that updates daily

### Docker Services

- **fetcher**: Runs once to populate initial data
- **mcp-server**: The MCP API server (port 8000)
- **fetcher-cron**: Runs daily to update data

### Managing Services

```bash
# View logs
docker-compose logs -f mcp-server
docker-compose logs -f fetcher-cron

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Kubernetes Deployment (Helm)

### Prerequisites
- Kubernetes cluster (k3s, minikube, etc.)
- Helm 3.x installed
- kubectl configured

### Quick Start

1. Navigate to the Helm chart:
```bash
cd deploy/helm/steam-librarian
```

2. Create a values override file:
```yaml
# values-override.yaml
steam:
  steamId: "YOUR_STEAM_ID"
  apiKey: "YOUR_STEAM_API_KEY"

# Optional: Customize storage
global:
  storageClass: "longhorn"  # Or your storage class
  storageSize: "1Gi"

# Optional: Set resource limits
mcpServer:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi

fetcher:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi
```

3. Install the chart:
```bash
helm install steam-librarian . -f values-override.yaml
```

### Configuration Options

#### Storage Configuration
```yaml
global:
  storageClass: "longhorn"  # Your storage class
  storageSize: "500Mi"      # Database size

# Or use existing PVC
persistence:
  existingClaim: "my-existing-pvc"
```

#### Fetcher Schedule
```yaml
fetcher:
  schedule: "0 2 * * *"     # Daily at 2 AM
  runOnStartup: true        # Run immediately on install
  cacheDays: 7              # Cache duration
  extraArgs:               # Additional fetcher arguments
    - "--friends"
```

#### Using Existing Secret
```yaml
steam:
  existingSecret: "my-steam-secret"
  existingSecretKeys:
    steamId: "steam-id"
    apiKey: "api-key"
```

#### Service Exposure
```yaml
mcpServer:
  service:
    type: ClusterIP  # or NodePort, LoadBalancer
    port: 8000
```

### Common Operations

#### Check Installation Status
```bash
# Get all resources
kubectl get all -l app.kubernetes.io/name=steam-librarian

# Check fetcher job status
kubectl get jobs -l app.kubernetes.io/component=fetcher-startup

# View MCP server logs
kubectl logs -f deployment/steam-librarian-mcp-server
```

#### Manual Fetcher Run
```bash
# Create a one-time job
kubectl create job --from=cronjob/steam-librarian-fetcher manual-fetch-$(date +%s)
```

#### Access MCP Server
```bash
# Port forward for local access
kubectl port-forward service/steam-librarian-mcp-server 8000:8000
```

#### Upgrade
```bash
helm upgrade steam-librarian . -f values-override.yaml
```

#### Uninstall
```bash
helm uninstall steam-librarian
```

### Troubleshooting

1. **PVC Issues**: Ensure your storage class supports RWO access mode
2. **Job Failures**: Check fetcher logs with `kubectl logs job/steam-librarian-fetcher-startup`
3. **Database Access**: Both services must mount the same PVC at `/data`

## Building Images

### Build Locally
```bash
# From project root
docker build -f deploy/docker/Dockerfile.fetcher -t steam-librarian-fetcher:latest .
docker build -f deploy/docker/Dockerfile.mcp_server -t steam-librarian-mcp-server:latest .
```

### Push to Registry
```bash
docker tag steam-librarian-fetcher:latest myregistry/steam-librarian-fetcher:latest
docker tag steam-librarian-mcp-server:latest myregistry/steam-librarian-mcp-server:latest

docker push myregistry/steam-librarian-fetcher:latest
docker push myregistry/steam-librarian-mcp-server:latest
```

Then update Helm values:
```yaml
fetcher:
  image:
    repository: myregistry/steam-librarian-fetcher
    tag: latest

mcpServer:
  image:
    repository: myregistry/steam-librarian-mcp-server
    tag: latest
```