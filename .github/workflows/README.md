# GitHub Actions Workflows

This repository uses GitHub Actions for CI/CD automation.

## Workflows

### 1. Build and Push Docker Images (`docker-build.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`
- Git tags matching `v*`
- Manual workflow dispatch

**What it does:**
- Builds multi-platform Docker images (amd64, arm64)
- Tags images based on branch/tag/SHA
- Pushes to GitHub Container Registry (ghcr.io)
- Uses GitHub Actions cache for faster builds

**Image naming:**
- `ghcr.io/jimsantora/steam-librarian/fetcher:TAG`
- `ghcr.io/jimsantora/steam-librarian/mcp-server:TAG`

### 2. Helm Chart Validation (`helm-lint.yml`)

**Triggers:**
- Changes to `deploy/helm/**`
- Pull requests with Helm changes
- Manual workflow dispatch

**What it does:**
- Lints the Helm chart
- Templates the chart with test values
- Validates generated Kubernetes manifests
- Runs Helm unit tests (if available)

### 3. Python Tests (`python-test.yml`)

**Triggers:**
- Changes to Python source code
- Pull requests with Python changes

**What it does:**
- Tests on Python 3.9, 3.10, 3.11
- Runs flake8 linting
- Validates imports
- Runs basic smoke tests

### 4. Release (`release.yml`)

**Triggers:**
- Push of tags matching `v*`

**What it does:**
- Updates Chart.yaml with release version
- Packages Helm chart
- Creates GitHub release with:
  - Helm chart tarball
  - Release notes
  - Docker image references
- Creates PR to update default image tags

### 5. Manual Docker Build (`docker-manual.yml`)

**Triggers:**
- Manual workflow dispatch only

**Inputs:**
- `tag`: Custom image tag
- `push`: Whether to push images
- `platforms`: Target platforms

**Use cases:**
- Testing builds without pushing
- Creating custom tagged images
- Building for specific platforms

## Image Tags

Images are tagged automatically based on the trigger:

- **Main branch**: `latest`, `main`, `sha-COMMIT`
- **Develop branch**: `develop`, `sha-COMMIT`
- **Pull requests**: `pr-NUMBER`
- **Tags**: `v1.2.3`, `1.2.3`, `1.2`, `1`, `latest`

## Secrets Required

The workflows use the following secrets:
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- No additional secrets required!

## Usage Examples

### Creating a Release

1. Tag your commit:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. The release workflow will:
   - Build and tag images as `v1.0.0`
   - Create a GitHub release
   - Package the Helm chart
   - Create a PR to update default versions

### Manual Build

1. Go to Actions → Manual Docker Build
2. Click "Run workflow"
3. Enter your custom tag (e.g., `test-feature`)
4. Choose whether to push
5. Run the workflow

### Testing Changes

1. Create a pull request
2. Workflows will automatically:
   - Build Docker images (tagged as `pr-NUMBER`)
   - Lint Helm charts
   - Run Python tests
   - Validate everything

## Deployment After Build

### Using the Built Images

After images are built and pushed to ghcr.io:

```bash
# Docker
docker run -e STEAM_ID=xxx -e STEAM_API_KEY=yyy \
  ghcr.io/jimsantora/steam-librarian/fetcher:latest

# Kubernetes with Helm
helm install steam-librarian ./deploy/helm/steam-librarian \
  --set fetcher.image.tag=v1.0.0 \
  --set mcpServer.image.tag=v1.0.0
```

### Image Pull Authentication

For private repositories, authenticate with ghcr.io:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

Or create a Kubernetes secret:

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=USERNAME \
  --docker-password=$GITHUB_TOKEN
```