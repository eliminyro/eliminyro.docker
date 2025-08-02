# Ansible Collection - eliminyro.docker

[![Molecule CI](https://github.com/eliminyro/eliminyro.docker/actions/workflows/main.yml/badge.svg)](https://github.com/eliminyro/eliminyro.docker/actions/workflows/main.yml)
[![Release](https://github.com/eliminyro/eliminyro.docker/actions/workflows/release.yml/badge.svg)](https://github.com/eliminyro/eliminyro.docker/actions/workflows/release.yml)
[![Ansible Galaxy](https://img.shields.io/badge/galaxy-eliminyro.docker-blue.svg)](https://galaxy.ansible.com/eliminyro/docker)

A comprehensive Ansible collection for Docker management, providing automated
setup, TLS configuration, and container deployment capabilities.

## Overview

This collection includes two main roles:

- **`setup`** - Configure Docker daemon with TLS, create custom networks, and
  validate configuration
- **`deploy`** - Deploy containerized applications with dependencies, volumes,
  and configuration management

## Requirements

- Ansible 2.15.0 or higher
- Python 3.x on the control node
- `community.general` collection
- Docker installed on target hosts

## Installation

### From Ansible Galaxy

```bash
ansible-galaxy collection install eliminyro.docker
```

### From Git Repository

```bash
ansible-galaxy collection install git+https://github.com/eliminyro/eliminyro.docker.git
```

### From Local Source

```bash
git clone https://github.com/eliminyro/eliminyro.docker.git
cd eliminyro.docker
ansible-galaxy collection build
ansible-galaxy collection install eliminyro-docker-*.tar.gz
```

## Roles

### setup

Configures Docker daemon with TLS certificates, custom networks, and security
settings.

**Key Features:**

- TLS certificate generation using CFSSL API
- Custom Docker network creation with IPAM configuration
- Docker daemon configuration and systemd service management
- TLS connectivity validation

**Example:**

```yaml
- hosts: docker_hosts
  become: True
  roles:
    - role: eliminyro.docker.setup
      vars:
        docker_tls_setup: True
        docker_net_setup: True
        cfssl_url: "https://cfssl.example.com"
        docker_server_name: "{{ ansible_fqdn }}"
        docker_networks:
          - name: mynet
            ipam_config:
              subnet: "172.30.0.0/16"
```

### deploy

Deploys containerized applications with support for dependencies, configuration
files, and volume management.

**Key Features:**

- Dynamic variable resolution based on application name
- Dependency container deployment
- Configuration file and template management
- Volume and network configuration
- Health checks and restart policies

**Example:**

```yaml
- hosts: docker_hosts
  roles:
    - role: eliminyro.docker.deploy
      vars:
        playbook_app: webapp
        webapp_image: nginx
        webapp_image_tag: latest
        webapp_ports:
          - "8080:80"
        webapp_volumes:
          - "/srv/webapp/data:/usr/share/nginx/html"
        webapp_networks:
          - name: "mynet"
        webapp_deps_run: True
        webapp_deps:
          - name: redis
            image: redis
            tag: "7"
            networks:
              - name: "mynet"
```

## Complete Workflow Example

```yaml
- name: Setup Docker with TLS and deploy application
  hosts: docker_hosts
  become: True
  tasks:
    # Setup Docker daemon and networks
    - name: Configure Docker with TLS
      include_role:
        name: eliminyro.docker.setup
      vars:
        docker_tls_setup: True
        docker_net_setup: True
        cfssl_url: "https://cfssl.internal.example.com"
        docker_networks:
          - name: appnet
            ipam_config:
              subnet: "172.25.0.0/16"

    # Deploy application stack
    - name: Deploy web application
      include_role:
        name: eliminyro.docker.deploy
      vars:
        playbook_app: myapp
        myapp_image: myorg/webapp
        myapp_image_tag: "1.2.3"
        myapp_ports:
          - "443:8080"
        myapp_networks:
          - name: appnet
        myapp_volumes:
          - "/srv/myapp/data:/app/data"
          - "/srv/myapp/config:/app/config"
        myapp_env:
          APP_ENV: production
          DB_HOST: postgres
        myapp_deps_run: True
        myapp_deps:
          - name: postgres
            image: postgres
            tag: "15"
            env:
              POSTGRES_DB: myapp
              POSTGRES_USER: appuser
              POSTGRES_PASSWORD: "{{ vault_db_password }}"
            volumes:
              - "/srv/postgres/data:/var/lib/postgresql/data"
            networks:
              - name: appnet
```

## Testing

This collection includes comprehensive testing using Molecule with multiple
scenarios:

```bash
# Test setup role
molecule test -s setup

# Test deploy role
molecule test -s deploy
```

## Documentation

Detailed documentation for each role is available in their respective README
files:

- [Setup Role Documentation](roles/setup/README.md)
- [Deploy Role Documentation](roles/deploy/README.md)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

GPL-3.0-or-later

## Author

[Pavel Eliminyro](https://bc.eliminyro.me)

## Support

- **Issues**:
  [GitHub Issues](https://github.com/eliminyro/eliminyro.docker/issues)
- **Repository**:
  [GitHub Repository](https://github.com/eliminyro/eliminyro.docker)
