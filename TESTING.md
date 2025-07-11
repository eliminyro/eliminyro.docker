# Testing

This collection uses [Molecule](https://molecule.readthedocs.io/) with [Testinfra](https://testinfra.readthedocs.io/) for comprehensive testing of both roles.

## Prerequisites

```bash
pip install molecule[docker] molecule-plugins[docker] testinfra pytest
pip install ansible-core>=2.15 docker requests cryptography
```

## Test Scenarios

### Setup Role Testing
Tests Docker daemon configuration, TLS setup, and network creation:

```bash
cd roles/setup
molecule test -s setup
```

**Test Coverage:**
- Docker daemon configuration validation
- TLS certificate generation and validation
- Custom network creation with IPAM
- SystemD service configuration
- Docker API connectivity over TLS

### Deploy Role Testing
Tests container deployment, configuration management, and service validation:

```bash
cd roles/deploy
molecule test -s deploy
```

**Test Coverage:**
- Container deployment and lifecycle management
- Volume mounting and configuration file deployment
- Network connectivity and isolation
- Environment variable configuration
- Multi-container dependency deployment
- Service health checks and startup validation

## Running Individual Test Phases

```bash
# Create test environment
molecule create -s <scenario>

# Run converge (apply the role)
molecule converge -s <scenario>

# Run tests only
molecule verify -s <scenario>

# Clean up
molecule destroy -s <scenario>
```

## Test Structure

```
molecule/
├── setup/
│   ├── molecule.yml          # Molecule configuration
│   ├── converge.yml          # Apply setup role
│   ├── prepare.yml           # Test environment setup
│   ├── cleanup.yml           # Test cleanup
│   ├── requirements.yml      # Collection dependencies
│   └── tests/                # Testinfra test files
└── deploy/
    ├── molecule.yml          # Molecule configuration
    ├── converge.yml          # Apply deploy role
    ├── prepare.yml           # Test environment setup
    ├── cleanup.yml           # Test cleanup
    ├── requirements.yml      # Collection dependencies
    └── tests/                # Testinfra test files
```

## Test Configuration

### Setup Scenario
- **Driver**: Local (uses Docker on host)
- **Provisioner**: Ansible
- **Verifier**: Testinfra
- **Dependencies**: CFSSL container for TLS testing

### Deploy Scenario
- **Driver**: Local (uses Docker on host)
- **Provisioner**: Ansible
- **Verifier**: Testinfra
- **Test Apps**: Nginx, Redis, PostgreSQL containers

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to master branch
- Manual workflow dispatch

The CI pipeline runs both scenarios in parallel and includes:
- Ansible lint validation
- Ansible sanity tests
- Full molecule test suite

## Writing Tests

Tests are written using [Testinfra](https://testinfra.readthedocs.io/) with pytest fixtures. Example:

```python
def test_docker_daemon_running(host):
    """Test that Docker daemon is running"""
    docker = host.service("docker")
    assert docker.is_running
    assert docker.is_enabled

def test_container_deployed(host, docker_client):
    """Test that container is deployed and running"""
    container = docker_client.containers.get("testapp")
    assert container.status == "running"
```

## Debugging Failed Tests

```bash
# Keep environment after failure for debugging
molecule test --destroy=never -s <scenario>

# Connect to test environment
docker exec -it molecule-local bash

# View test logs
molecule test -s <scenario> -- -v
```

## Local Development

For faster development iterations:

```bash
# Create environment once
molecule create -s <scenario>

# Iteratively test changes
molecule converge -s <scenario>
molecule verify -s <scenario>

# Cleanup when done
molecule destroy -s <scenario>
```