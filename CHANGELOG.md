# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-08-02

### Changes

- [FIX] Fix READMEs for privacy. (0f5cfec)

## [1.0.0] - 2025-08-01

### Changes

- [MAJOR] Added roles 'deploy' and 'setup', added molecule test suite for both.
  (c0aa1de)

### Added

- Initial release of the eliminyro.docker collection
- `setup` role for Docker daemon configuration and TLS setup
- `deploy` role for container deployment and management
- Comprehensive molecule testing for both roles
- TLS certificate generation and validation
- Docker network creation and management
- Container deployment with volume and configuration management
- GitHub Actions CI/CD pipeline with lint, sanity, and molecule tests

### Features

- **Docker TLS Setup**: Automated TLS certificate generation and Docker daemon
  configuration
- **Network Management**: Create and manage custom Docker networks with IPAM
  configuration
- **Container Deployment**: Deploy containers with configurable volumes,
  networks, and restart policies
- **Configuration Management**: Template-based configuration file deployment to
  containers
- **Service Validation**: Comprehensive testing of Docker daemon, TLS
  connectivity, and container health

### Testing

- Molecule scenarios for both setup and deployment workflows
- Testinfra-based functional testing
- TLS certificate validation using cryptography library
- Docker API connectivity testing using requests library
- Network isolation and connectivity verification
- Container deployment and configuration validation

### Documentation

- Role-specific README files
- Molecule scenario documentation

## [0.1.0] - Initial Alpha state

### Added

- First stable version of eliminyro.docker collection
- Working Docker setup and deployment automation
- Full TLS support with certificate management (cfssl provider required)
- Container orchestration capabilities
